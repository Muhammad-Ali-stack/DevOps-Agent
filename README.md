# DevOps Agent

A multi-agent DevOps and infrastructure monitoring portfolio project.

## Project layout

- `backend/` — FastAPI server and Python agent logic
  - `agents/` — one file per agent
  - `core/` — shared orchestration and LLM abstraction
  - `api/` — FastAPI routes
  - `data/sample_logs/` — synthetic log fixtures for testing
- `frontend/` — React + Vite + TypeScript dashboard

## Backend setup

```bash
cd backend
python -m venv .venv
# Windows PowerShell
.\.venv\Scripts\Activate.ps1
# macOS/Linux
source .venv/bin/activate
pip install -r requirements.txt
```

Create a local `.env` file in the backend folder from `.env.example` and add your API keys:

```bash
cd backend
copy .env.example .env
```

Then update the values:

```env
GEMINI_API_KEY=your_gemini_api_key_here
GROQ_API_KEY=your_groq_api_key_here
```

## Run FastAPI

```bash
cd backend
uvicorn main:app --reload
```

Visit:

- `http://localhost:8000/health`

## Frontend setup

```bash
cd frontend
npm install
npm run dev
```

## Current status

This scaffold includes:

- a working FastAPI app with a health endpoint
- a deterministic log watcher agent for anomaly detection
- sample log fixtures for timeout, null-pointer, and latency/memory-leak scenarios
- a basic environment file template

## Next steps

- add the Gemini/Groq LLM abstraction
- add the root-cause analysis and fix-drafting agents
- wire a dashboard to surface anomalies and diagnoses
