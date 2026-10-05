import os

from chainlite import get_all_configured_engines
from chainlite.llm_config import GlobalVars

from corpora import corpus_id_to_corpus_object
from tasks.defaults import CHATBOT_DEFAULT_CONFIG

get_all_configured_engines()

# ChainLite maps stable engine names to provider model IDs. Keep the engine stable
# while allowing the OpenRouter model and endpoint to be configured in .env.
for endpoint in GlobalVars.all_llm_endpoints:
    if "openrouter" in endpoint["engine_map"]:
        model = os.getenv("OPENROUTER_MODEL", "openrouter/free").strip()
        endpoint["engine_map"]["openrouter"] = f"openrouter/{model}"
        endpoint["api_base"] = os.getenv(
            "OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"
        ).strip()
        break

all_configured_engines = GlobalVars.get_all_configured_engines()


def add_pipeline_arguments(parser):
    parser.add_argument(
        "--engine",
        type=str,
        required=True,
        choices=all_configured_engines,
        help="The LLM engine to use.",
    )

    # determine components of the pipeline
    parser.add_argument(
        "--do_refine", action="store_true", help="Whether to refine the final response."
    )
    parser.add_argument(
        "--corpus_id",
        type=str,
        default=None,
        help="The corpus ID to search for information.",
    )
    parser.add_argument(
        "--retriever_endpoint",
        type=str,
        default=None,
        help="The endpoint to send retrieval requests to. Defaults to the one defined in Corpus.",
    )

    # Retrieval parameters
    parser.add_argument(
        "--do_reranking",
        action="store_true",
        default=CHATBOT_DEFAULT_CONFIG["do_reranking"],
        help="Whether we should rerank the search results.",
    )
    parser.add_argument(
        "--query_pre_reranking_num",
        type=int,
        default=CHATBOT_DEFAULT_CONFIG["query_pre_reranking_num"],
        help="Number of passages to retrieve before reranking. Will have no effect if `do_reranking` is False",
    )
    parser.add_argument(
        "--query_post_reranking_num",
        type=int,
        default=CHATBOT_DEFAULT_CONFIG["query_post_reranking_num"],
        help="Number of passages to retrieve when searching for information.",
    )
    parser.add_argument(
        "--claim_pre_reranking_num",
        type=int,
        default=CHATBOT_DEFAULT_CONFIG["claim_pre_reranking_num"],
        help="Number of evidences to retrieve per LLM claim before reranking. Will have no effect if `do_reranking` is False",
    )
    parser.add_argument(
        "--claim_post_reranking_num",
        type=int,
        default=CHATBOT_DEFAULT_CONFIG["claim_post_reranking_num"],
        help="Number of evidences to retrieve per claim.",
    )


def check_pipeline_arguments(args):
    if args.do_reranking:
        if (
            args.query_pre_reranking_num is None
            or args.query_pre_reranking_num < args.query_post_reranking_num
        ):
            raise ValueError(
                "When retrieval reranking is enabled, you need to specify a `--query_pre_reranking_num` >= `--query_post_reranking_num`"
            )

        if (
            args.claim_pre_reranking_num is None
            or args.claim_pre_reranking_num < args.claim_post_reranking_num
        ):
            raise ValueError(
                "When evidence reranking is enabled, you need to specify a `--claim_pre_reranking_num` >= `--claim_post_reranking_num`"
            )
    if args.retriever_endpoint is None:
        corpus_object = corpus_id_to_corpus_object(args.corpus_id)
        args.retriever_endpoint = corpus_object.overwritten_parameters[
            "retriever_endpoint"
        ]
