# VeriQuest AI

VeriQuest AI is a source-aware research chatbot. It looks up relevant public information from Wikipedia, optionally adds Google Custom Search results, and uses an OpenRouter-hosted language model to produce a clear answer with available sources.

The web app is built for local use and runs at `http://127.0.0.1:5001`.

## Put VeriQuest AI online for free (Render)

This repository is ready for a free [Render](https://render.com) web-service
deployment. Render suits this Python/Chainlit app better than Vercel because it
runs a persistent web process with its Socket.IO chat connection.

1. Create a new GitHub repository and upload this entire `VeriQuest-AI` folder.
   Do **not** upload `.env` or your API key.
2. Sign in to Render with GitHub, select **New +** → **Blueprint**, and choose
   that repository. Render will detect `render.yaml` and the Docker setup.
3. Keep the free plan selected. In the environment-variable screen, set
   `OPENROUTER_API_KEY` to your private OpenRouter key. Do not add it to GitHub.
4. Click **Apply**. When the deployment finishes, Render gives you a public
   `https://...onrender.com` URL.

The free service sleeps after inactivity, so its first request after a pause can
take around a minute. The free service has temporary disk storage: the recent
chat cards remain while that instance is running, but can disappear after a
restart or redeploy. Permanent shared history needs an external database, which
is a separate hosting decision.

## What the project uses

| Area | Technology | Purpose |
| --- | --- | --- |
| Web interface | Chainlit, HTML/CSS/JavaScript | Chat UI, session handling, and the VeriQuest visual theme |
| Backend | Python 3.11, Chainlit | Receives messages and coordinates the answer pipeline |
| AI model | OpenRouter, LiteLLM/Chainlite, LangChain, LangGraph | Sends prompts to the configured LLM and manages the response flow |
| Knowledge retrieval | Wikipedia REST API | Finds current Wikipedia search results and summaries directly|
| Optional web search | Google Programmable Search JSON API | Adds Google web result snippets when configured |
| Optional advanced retrieval | Qdrant, Hugging Face Transformers, ONNX Runtime | Supports local vector-search workflows; it is not required for normal direct-Wikipedia chat |
| Data and operations | Pydantic, Loguru, Redis client, Cosmos DB support | Validation, logging, caching support, and optional conversation persistence |
| Environment management | Conda / Miniforge | Creates the reproducible Python environment |

## Requirements

- macOS, Linux, or Windows with a working terminal
- [Miniforge or Conda](https://github.com/conda-forge/miniforge)
- An OpenRouter API key
- Internet access for Wikipedia, OpenRouter, and optional Google search

## Start the project on this laptop

Open **Terminal** and run these commands exactly:

```bash
cd /Users/dhruvgulati/Downloads/VeriQuest-AI
source /opt/homebrew/Caskroom/miniforge/base/bin/activate veriquest-ai
chainlit run backend_server.py --port 5001
```

Then open this address in a browser:

```text
http://127.0.0.1:5001
```

Keep the Terminal window open while using the app. To stop the server, return to that Terminal window and press `Control + C`.

### If `conda activate` is already configured

You can use the shorter command instead of `source ...`:

```bash
cd /Users/dhruvgulati/Downloads/VeriQuest-AI
conda activate veriquest-ai
chainlit run backend_server.py --port 5001
```

## First-time setup or setup on another computer

### 1. Open the project folder

```bash
cd /path/to/VeriQuest-AI
```

### 2. Create the Conda environment

```bash
conda env create -f conda_env.yaml
conda activate veriquest-ai
```

If Conda says the environment already exists, skip the creation command and only activate it.

### 3. Create the private configuration file

```bash
cp .env.example .env
```

Open `.env` in an editor and set your OpenRouter key:

```dotenv
OPENROUTER_API_KEY=your_openrouter_key_here
OPENROUTER_MODEL=openrouter/free
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
```

Do not commit or share `.env`; it contains your private API key.

### 4. Start VeriQuest AI

```bash
chainlit run backend_server.py --port 5001
```

## Optional Google search configuration

Wikipedia retrieval works with no additional search key. To include Google results as an extra source, add both of the following values to `.env`:

```dotenv
GOOGLE_SEARCH_API_KEY=your_google_api_key
GOOGLE_SEARCH_ENGINE_ID=your_programmable_search_engine_id
```

Restart the server after changing `.env`.

## Common problems

### `conda: command not found`

Install Miniforge/Conda, then reopen Terminal. On this laptop, Miniforge is installed under `/opt/homebrew/Caskroom/miniforge/base`.

### `Address already in use` for port 5001

Another local server is already running. Find it and stop it:

```bash
lsof -nP -iTCP:5001 -sTCP:LISTEN
kill <PID>
```

Then start VeriQuest AI again.

### The model says it is rate-limited or unavailable

This is an OpenRouter provider/quota response, not a frontend failure. Wait for the quota reset, choose a model with available capacity in `.env`, or add OpenRouter credits. Restart the server after changing `OPENROUTER_MODEL`.

### The app opens but cannot find sources

Check your internet connection. Wikipedia or Google can temporarily rate-limit requests. The assistant will show a retrieval-related message when a source lookup cannot complete.

### The browser still shows an old interface

Hard-refresh the page with `Command + Shift + R` on macOS or `Ctrl + Shift + R` on Windows/Linux.

## Important project files

| File or folder | Description |
| --- | --- |
| `backend_server.py` | Chainlit application entry point |
| `corpora.py` | Chat profile, source description, and starter prompts |
| `pipelines/chatbot.py` | Answer generation and source-aware chat pipeline |
| `retrieval/retriever_api.py` | Direct Wikipedia and optional Google retrieval code |
| `.env` | Private local API configuration; never commit it |
| `.env.example` | Safe configuration template |
| `data/veriquest_ai.sqlite3` | Local SQLite archive of completed chat messages, created automatically |
| `conda_env.yaml` | Conda environment definition |
| `.chainlit/config.toml` | Chainlit settings, app name, and custom asset paths |
| `public/css/veriquest-ai.css` | VeriQuest AI visual styling |
| `public/js/veriquest-ai.js` | Small frontend branding and composer enhancements |

## Notes

- The direct Wikipedia mode is the default source path. 
- Google search is optional and requires its own Google credentials.
- Cosmos DB is optional. If it is not configured, the app remains usable but does not persist conversations remotely.
- Completed chats are always saved locally on this laptop in `data/veriquest_ai.sqlite3`. This file is private and excluded from Git.
