# SlothDesk Backend

The FastAPI backend for **SlothDesk** — a local-first, privacy-respecting AI file organizer. It scans a configured local directory, uses a local open-weight language model via [Ollama](https://ollama.com) to propose a structured organization plan, and executes verified moves only after explicit user confirmation.

---

## Features

- **Local AI Classification**: Queries a local LLM (`qwen3:4b` via Ollama) using structured JSON output to organize unorganized files into logical subdirectories.
- **Rich Organization Categories**:
  - **`Documents`**: General documents, PDF manuals, Word documents (`.pdf`, `.doc`, `.docx`, `.odt`, `.rtf`, `.tex`).
  - **`Images`**: Pictures and screenshots (`.jpg`, `.jpeg`, `.png`, `.gif`, `.webp`, `.svg`, `.bmp`, `.tiff`, `.heic`).
  - **`Audio`**: Songs, recordings, and audio files (`.mp3`, `.wav`, `.flac`, `.aac`, `.ogg`, `.m4a`, `.wma`, `.aiff`, `.opus`, etc.).
  - **`Video`**: Movies, clips, and recordings (`.mp4`, `.m4v`, `.mkv`, `.avi`, `.mov`, `.wmv`, `.webm`, `.flv`, `.mpeg`, etc.).
  - **`Code`**: Source code files, scripts, and markup (`.py`, `.js`, `.ts`, `.tsx`, `.jsx`, `.cpp`, `.c`, `.h`, `.java`, `.rs`, `.go`, `.html`, `.css`, `.sh`, etc.).
  - **`Data`**: Databases, tabular datasets, analytics, and configs (`.json`, `.csv`, `.tsv`, `.sql`, `.sqlite`, `.parquet`, `.xml`, `.yaml`, `.xlsx`, etc.).
  - **`Invoices`**: Receipts, payment notices, and billing files.
  - **`Resumes`**: CVs, resumes, and job application profiles.
  - **`Notes`**: Documentation, memos, and markdown notes (`.md`, `notes.txt`).
  - **`Other`**: Miscellaneous files that do not cleanly fit other categories.
- **Two-Phase Non-Destructive Execution**: Validates all actions across 10 security checks before initiating moves. Employs pre-move SHA-256 fingerprint verification and best-effort rollback on failure.
- **Duplicate Detection**: Fast SHA-256 content hashing to identify duplicate files without reading contents unnecessarily.
- **Audit Logging**: Persists all completed moves, skipped items, and operation metrics to SQLite.
- **Strict Security Model**:
  - Restricts operations exclusively to `SLOTHDESK_ROOT`.
  - Rejects path traversal (`..`), symlinks, and absolute destination paths.
  - Independent server-side plan validation (AI output is never blindly trusted).
  - Never deletes files.

---

## Tech Stack

- **Framework**: [FastAPI](https://fastapi.tiangolo.com/) + [Uvicorn](https://www.uvicorn.org/)
- **Data Validation**: [Pydantic v2](https://docs.pydantic.dev/) + `pydantic-settings`
- **HTTP Client**: [HTTPX](https://www.python-httpx.org/) (async requests to Ollama API)
- **Database**: SQLite3 (audit history and operations log)
- **Local AI Provider**: [Ollama](https://ollama.com) running `qwen3:4b`
- **Testing**: [pytest](https://docs.pytest.org/) + `pytest-asyncio` (67 unit tests)

---

## Getting Started

### 1. Prerequisites

- macOS / Linux with Python 3.9+
- [Ollama](https://ollama.com) installed and running locally
- Ollama model `qwen3:4b` downloaded

```bash
# Start Ollama service (if not already running)
ollama serve

# Pull the model
ollama pull qwen3:4b
```

### 2. Environment Setup

Create and activate a virtual environment:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. Configuration

Copy the example configuration:

```bash
cp .env.example .env
```

Edit `.env` to configure your settings:

```env
# Path to the directory you want to organize
SLOTHDESK_ROOT=~/Downloads

# Ollama local endpoint and model
OLLAMA_URL=http://127.0.0.1:11434
OLLAMA_MODEL=qwen3:4b
OLLAMA_TIMEOUT_SECONDS=180

# Safety limits
MAX_SCAN_FILES=500
MAX_FILE_SIZE_MB=50
MAX_PLAN_ACTIONS=100
```

### 4. Running the Server

Start the FastAPI application with Uvicorn:

```bash
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

- API Base: `http://127.0.0.1:8000`
- Interactive OpenAPI Docs: `http://127.0.0.1:8000/docs`

---

## API Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/health` | Backend health, active model, and configured root directory |
| `GET` | `/api/ollama/status` | Ollama service and model availability status |
| `GET` | `/api/scan` | Scans `SLOTHDESK_ROOT` and returns file inventory |
| `POST` | `/api/plan` | Generates AI classification plan for scanned files (non-destructive) |
| `POST` | `/api/apply` | Executes user-approved file moves with rollback protection |
| `GET` | `/api/history` | Paginated history of applied operations from SQLite |
| `GET` | `/api/stats` | Aggregated metrics (files scanned, move success/failure counts) |
| `GET` | `/api/duplicates` | Scans for duplicate files via SHA-256 hashes |

---

## Testing

Run the comprehensive unit test suite:

```bash
source .venv/bin/activate
python -m pytest tests/ -v
```

All 67 tests use isolated temporary directories and mocked Ollama responses — no live model required, no real files modified.

---

## Architecture

```
backend/
├── app/
│   ├── main.py            # FastAPI application, CORS, exception handlers, lifecycle
│   ├── config.py          # Settings validation and path resolution via Pydantic
│   ├── schemas.py         # Request and response models, FileCategory enum
│   ├── database.py        # SQLite database connection and schema setup
│   ├── api/
│   │   └── routes.py      # Route definitions for all endpoints
│   ├── security/
│   │   └── paths.py       # Path traversal guards, symlink checks, root boundary checks
│   └── services/
│       ├── scanner.py     # Directory scanning, file-type classification, hashing
│       ├── ollama.py      # Async HTTP client for Ollama API with typed error handling
│       ├── ai.py          # AI prompt generation, JSON schema, response parser
│       ├── planner.py     # Server-side validation of proposed move actions
│       ├── organizer.py   # Two-phase file mover with fingerprinting & rollback
│       └── history.py     # SQLite persistence for operation records and statistics
├── tests/                 # 67 unit and integration tests covering all modules
├── requirements.txt       # Python dependencies
└── pyproject.toml         # Tooling and pytest configuration
```

---

## Security Model

1. **Sandboxed Root**: All operations are strictly constrained within `SLOTHDESK_ROOT`. Any attempt to escape via relative paths (`../`) or symlinks is rejected.
2. **Untrusted AI Output**: The AI model is never trusted to enforce security rules. All proposed actions undergo independent server-side validation.
3. **No Deletions**: The application only performs directory creation and file relocation (`move/rename`). It contains no file deletion capability.
4. **Untrusted Filenames**: File names and metadata are treated as data, preventing prompt injection attacks against the local model.
5. **Localhost Only**: Binds strictly to `127.0.0.1` with restricted CORS headers.
