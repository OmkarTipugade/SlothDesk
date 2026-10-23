# SlothDesk Backend

Local-first AI file organizer backend — a **Hacktoberfest 2026 "Slow and Steady"** project.

SlothDesk helps you organize files in a selected directory using a locally running open-weight AI model.  Your files never leave your machine.

## Quick Start

### 1. Prerequisites

- macOS with Python 3.9+
- [Ollama](https://ollama.com) installed and running
- The `qwen3:4b` model downloaded

```bash
# Start Ollama (if not already running)
ollama serve

# Download the model
ollama pull qwen3:4b

# Verify
ollama list
```

### 2. Install Dependencies

```bash
cd backend
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. Configure

Copy the example environment file and adjust if needed:

```bash
cp .env.example .env
```

Key settings in `.env`:

| Variable | Default | Description |
|---|---|---|
| `SLOTHDESK_ROOT` | `~/SlothDesk_Demo` | Directory to organize |
| `OLLAMA_URL` | `http://127.0.0.1:11434` | Local Ollama endpoint |
| `OLLAMA_MODEL` | `qwen3:4b` | Ollama model name |
| `OLLAMA_TIMEOUT_SECONDS` | `120` | Request timeout |
| `MAX_SCAN_FILES` | `500` | Maximum files to scan |

> **Important:** `SLOTHDESK_ROOT` defaults to a dedicated `~/SlothDesk_Demo` folder, not your home directory or Downloads.

### 4. Set Up Demo Files

Create some sample files to test with:

```bash
mkdir -p ~/SlothDesk_Demo
cd ~/SlothDesk_Demo

# Create sample files
echo "Q3 Financial Report" > quarterly_report.pdf
echo "Meeting notes from standup" > standup_notes.txt
echo "John Doe Resume" > john_doe_resume.docx
echo "Invoice #1234" > invoice_march_2024.pdf
cp /System/Library/Desktop\ Pictures/*.heic . 2>/dev/null || true
```

### 5. Start the Backend

```bash
cd backend
source .venv/bin/activate
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

The API is available at `http://127.0.0.1:8000`.  Interactive docs at `http://127.0.0.1:8000/docs`.

### 6. Run the Frontend

In a separate terminal:

```bash
cd frontend
npm run dev
```

Open `http://localhost:5173` in your browser.

## API Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/health` | Backend health + config |
| `GET` | `/api/ollama/status` | Ollama & model availability |
| `GET` | `/api/scan` | Scan directory → file inventory |
| `POST` | `/api/plan` | AI classification → validated plan |
| `POST` | `/api/apply` | Execute approved file moves |
| `GET` | `/api/history` | Paginated operation history |
| `GET` | `/api/stats` | Aggregate metrics |
| `GET` | `/api/duplicates` | SHA-256 duplicate detection |

### Example Requests

```bash
# Health check
curl http://127.0.0.1:8000/api/health

# Scan files
curl http://127.0.0.1:8000/api/scan

# Generate AI plan
curl -X POST http://127.0.0.1:8000/api/plan

# Apply selected actions
curl -X POST http://127.0.0.1:8000/api/apply \
  -H "Content-Type: application/json" \
  -d '{"actions": [{"source": "report.pdf", "destination": "Documents/report.pdf", "category": "Documents", "reason": "PDF document"}], "confirmed": true}'

# History (page 1, 20 per page)
curl "http://127.0.0.1:8000/api/history?page=1&page_size=20"

# Duplicates
curl http://127.0.0.1:8000/api/duplicates
```

## Testing

```bash
source .venv/bin/activate
python -m pytest tests/ -v
```

All tests use temporary directories and mocked Ollama — no live model required, no real files touched.

### Optional: Live Ollama Integration Test

If Ollama is running with `qwen3:4b` available:

```bash
python -m pytest tests/ -v -k "integration" --run-integration
```

## Troubleshooting

| Problem | Solution |
|---|---|
| "Ollama is not running" | Run `ollama serve` or open the Ollama app |
| "Model not found" | Run `ollama pull qwen3:4b` |
| "SLOTHDESK_ROOT does not exist" | Create the directory or update `.env` |
| Timeout errors | Increase `OLLAMA_TIMEOUT_SECONDS` in `.env` |
| CORS errors in browser | Ensure backend runs on port 8000 and frontend on 5173 |

## Architecture

```
backend/
  app/
    main.py            ← FastAPI app, CORS, startup, exception handlers
    config.py          ← Validated settings from .env
    schemas.py         ← Pydantic v2 request/response models
    database.py        ← SQLite initialization and connection
    api/
      routes.py        ← All API endpoints
    services/
      ollama.py        ← Ollama HTTP client with typed exceptions
      scanner.py       ← File discovery, hashing, duplicate detection
      ai.py            ← AI prompt building and response parsing
      planner.py       ← Server-side plan validation (13 checks)
      organizer.py     ← Two-phase file mover with rollback
      history.py       ← SQLite persistence and pagination
    security/
      paths.py         ← Path traversal prevention, symlink rejection
  tests/               ← 65 tests covering all modules
```

## Security Model

- All file operations restricted to `SLOTHDESK_ROOT`
- Path traversal and symlink rejection at every layer
- AI model output is never trusted — independent server-side validation
- Filenames treated as untrusted data (prompt injection defense)
- No shell execution, no file deletion, no cloud AI
- CORS restricted to local frontend origins
- Backend binds to `127.0.0.1` only
- No automatic execution — user must explicitly confirm

## Known Limitations

- Filesystem operations are not truly atomic; a crash mid-batch may leave partial results
- Cross-filesystem moves copy-then-delete (not atomic)
- Concurrent filesystem modifications by other processes are detected but not prevented
- Rollback is best-effort; rollback failures are reported but files stay at their new location
- The AI model may produce suboptimal categorizations depending on filenames
- No authentication (localhost-only by design)
