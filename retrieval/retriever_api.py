import logging
import os
import re
from urllib.parse import quote

import requests
from tqdm import trange

from retrieval.retrieval_commons import QueryResult, SearchResultBlock

logger = logging.getLogger(__name__)

WIKIPEDIA_API_USER_AGENT = "VeriQuest-AI/1.0 (Wikipedia retrieval fallback)"


def _focused_wikipedia_query(query: str) -> str | None:
    """Turn a natural-language question into a better Wikipedia title search.

    Wikipedia's search endpoint can overemphasize generic words such as
    ``founder`` or ``effect``. For example, "who was founder of cell theory"
    should search for "cell theory", not for every page containing "founder".
    """
    normalized = re.sub(r"\s+", " ", query.strip())
    patterns = [
        r"^(?:who|what) (?:was|were|is|are) (?:the )?(?:founder|founders|creator|creators) of (.+?)\??$",
        r"^(?:who|what) (?:discovered|developed|invented) (.+?)\??$",
        r"^(?:tell me about|explain|define) (.+?)\??$",
    ]
    for pattern in patterns:
        match = re.match(pattern, normalized, flags=re.IGNORECASE)
        if match:
            subject = match.group(1).strip(" ?.")
            if len(subject) >= 3:
                return subject
    return None


def _article_extract(rest_url: str, title: str, headers: dict[str, str]) -> str:
    """Fetch enough plain article text to answer questions beyond the lead.

    The REST summary is useful for short definitions but often omits the exact
    detail a question asks for (for example, the scientists in cell theory).
    """
    response = requests.get(
        f"{rest_url}/w/api.php",
        params={
            "action": "query",
            "prop": "extracts",
            "explaintext": 1,
            "exchars": 3500,
            "titles": title,
            "format": "json",
        },
        headers=headers,
        timeout=20,
    )
    response.raise_for_status()
    pages = response.json().get("query", {}).get("pages", {})
    page = next(iter(pages.values()), {})
    return page.get("extract", "")


def _retrieve_from_wikipedia(
    queries: list[str], num_blocks: int, languages: list[str]
) -> list[QueryResult]:
    """Retrieve cited Wikipedia extracts without relying on the demo server.

    This is deliberately a small fallback for the default Wikipedia corpus. It
    keeps the existing RAG stages and citation UI intact when the public
    Stanford retriever is unavailable.
    """
    language = languages[0] if languages else "en"
    rest_url = f"https://{language}.wikipedia.org"
    headers = {"User-Agent": WIKIPEDIA_API_USER_AGENT}
    results = []

    for query in queries:
        search_queries = [query]
        focused_query = _focused_wikipedia_query(query)
        if focused_query and focused_query.casefold() != query.casefold():
            # Search the topic first, then keep original-query matches as extras.
            search_queries.insert(0, focused_query)

        search_items = []
        seen_keys = set()
        for search_query in search_queries:
            search_response = requests.get(
                f"{rest_url}/w/rest.php/v1/search/page",
                params={"q": search_query, "limit": num_blocks},
                headers=headers,
                timeout=20,
            )
            search_response.raise_for_status()
            for page in search_response.json().get("pages", []):
                page_key = page.get("key")
                if page_key and page_key not in seen_keys:
                    seen_keys.add(page_key)
                    search_items.append(page)
                if len(search_items) >= num_blocks:
                    break
            if len(search_items) >= num_blocks:
                break
        if not search_items:
            results.append(QueryResult())
            continue

        search_results = []
        for rank, page in enumerate(search_items):
            title = page.get("title")
            page_key = page.get("key")
            if not title or not page_key:
                continue
            summary_response = requests.get(
                f"{rest_url}/api/rest_v1/page/summary/{quote(page_key)}",
                headers=headers,
                timeout=20,
            )
            summary_response.raise_for_status()
            summary = summary_response.json()
            try:
                content = _article_extract(rest_url, title, headers)
            except requests.RequestException as exc:
                logger.warning("Full Wikipedia extract failed for %s: %s", title, exc)
                content = summary.get("extract", "")
            if not content:
                continue
            search_results.append(
                SearchResultBlock(
                    document_title=title,
                    section_title="",
                    content=content,
                    url=summary.get("content_urls", {})
                    .get("desktop", {})
                    .get("page")
                    or f"https://{language}.wikipedia.org/wiki/{quote(title.replace(' ', '_'))}",
                    similarity_score=1 / (rank + 1),
                    probability_score=1 / (rank + 1),
                )
            )
        results.append(QueryResult(results=search_results))

    return results


def _retrieve_from_google(queries: list[str], num_blocks: int) -> list[QueryResult]:
    """Optionally add Google Programmable Search results as cited web sources."""
    api_key = os.getenv("GOOGLE_SEARCH_API_KEY", "").strip()
    search_engine_id = os.getenv("GOOGLE_SEARCH_ENGINE_ID", "").strip()
    if not api_key or not search_engine_id:
        return [QueryResult() for _ in queries]

    results = []
    for query in queries:
        response = requests.get(
            "https://www.googleapis.com/customsearch/v1",
            params={
                "key": api_key,
                "cx": search_engine_id,
                "q": query,
                "num": min(num_blocks, 10),
            },
            timeout=10,
        )
        response.raise_for_status()
        blocks = []
        for rank, item in enumerate(response.json().get("items", [])):
            title, snippet, url = item.get("title"), item.get("snippet"), item.get("link")
            if title and snippet and url:
                blocks.append(
                    SearchResultBlock(
                        document_title=title,
                        section_title="Google Search",
                        content=snippet,
                        url=url,
                        similarity_score=1 / (rank + 1),
                        probability_score=1 / (rank + 1),
                    )
                )
        results.append(QueryResult(results=blocks))
    return results


def retrieve_via_api(
    queries: str | list[str],
    retriever_endpoint: str,
    do_reranking: bool,
    pre_reranking_num: int,
    post_reranking_num: int,
    languages: str | list[str] = [],
    batch_size: int = 10,
    additional_search_filters: list[dict] = [],
) -> list[QueryResult]:
    """
    Retrieve search results from a retriever API.
    Args:
        queries (str | list[str]): A single query or a list of queries to be sent to the retriever.
        retriever_endpoint (str): The endpoint URL of the retriever API.
        do_reranking (bool): Flag indicating whether to perform reranking on the results.
        pre_reranking_num (int): Number of blocks to consider before reranking.
        post_reranking_num (int): Number of blocks to return after reranking.
        languages (str | list[str], optional): A single language or a list of languages to filter the search results. Defaults to [], meaning search in all languages.
        batch_size (int, optional): Number of queries to send in each batch. Defaults to 10.
        additional_search_filters (list[dict]): Additional search filters. Defaults to [], meaning no addition filters apart from language filters.
    Returns:
        list[QueryResult]: A list of QueryResult objects containing the search results for each query.
    Raises:
        Exception: If the rate limit is reached or if there is an error with the retriever API request.
    """

    if not isinstance(queries, list):
        queries = [queries]
    if not isinstance(languages, list):
        languages = [languages]

    ret = []
    if retriever_endpoint == "direct://wikipedia":
        wikipedia_results = _retrieve_from_wikipedia(
            queries, post_reranking_num, languages
        )
        try:
            google_results = _retrieve_from_google(queries, post_reranking_num)
        except requests.RequestException as exc:
            logger.warning("Google Search retrieval failed: %s", exc)
            google_results = [QueryResult() for _ in queries]
        for wikipedia, google in zip(wikipedia_results, google_results):
            ret.append(
                QueryResult(
                    results=(wikipedia.results + google.results)[:post_reranking_num]
                )
            )
        return ret

    for i in trange(
        0,
        len(queries),
        batch_size,
        disable=len(queries) <= batch_size,
        desc="Retrieving",
    ):
        batch_queries = queries[i : i + batch_size]
        try:
            response = requests.post(
                retriever_endpoint,
                json={
                    "query": batch_queries,
                    "rerank": do_reranking,
                    "num_blocks_to_rerank": pre_reranking_num,
                    "num_blocks": post_reranking_num,
                    "search_filters": [
                        {"field_name": "language", "filter_type": "eq", "field_value": lang}
                        for lang in languages
                    ]
                    + additional_search_filters,
                },
                timeout=5,
            )
            response.raise_for_status()
            results = response.json()
            assert len(results) == len(batch_queries), (
                f"Number of queries and results do not match. Length of queries: {len(batch_queries)}, Length of results: {len(results)}"
            )
            for j in range(len(batch_queries)):
                search_results = [SearchResultBlock(**r) for r in results[j]["results"]]
                ret.append(QueryResult(results=search_results))
        except (requests.RequestException, ValueError, KeyError, AssertionError) as exc:
            # The hosted Stanford retriever is a public demo and can be down.
            # Fall back only for its Wikipedia corpus, never for another corpus.
            if "wikipedia_" not in retriever_endpoint:
                raise RuntimeError(f"Retriever API request failed: {exc}") from exc
            logger.warning(
                "Hosted retriever failed (%s); using the Wikipedia API fallback.", exc
            )
            ret.extend(
                _retrieve_from_wikipedia(
                    batch_queries, post_reranking_num, languages
                )
            )

    return ret
