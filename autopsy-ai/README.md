# 🔬 Autopsy AI — Senior Developer in a Box
### Team 7 | Built with Python FastAPI + Anthropic Claude

---

## What Is This?
Autopsy AI is an AI-powered code review platform (like CodeRabbit) that automatically:
- **Reviews** your code for quality issues and code smells
- **Writes** unit tests covering edge cases
- **Audits** for security vulnerabilities (OWASP Top 10)
- **Generates** professional README and technical documentation

---

## Project Structure
```
autopsy-ai/
├── backend/
│   ├── main.py              ← FastAPI server entry point
│   ├── ai_helper.py         ← Shared Claude API caller
│   ├── requirements.txt     ← Python dependencies
│   ├── .env                 ← Your API key (create this!)
│   └── routes/
│       ├── __init__.py      ← Makes routes/ a Python package
│       ├── reviewer.py      ← Week 1: Code quality analysis
│       ├── tester.py        ← Week 2: Unit test generation
│       ├── bug_hunter.py    ← Week 3: Security audit
│       └── documenter.py    ← Week 4: Documentation generation
├── frontend/
│   ├── index.html           ← Main UI (structure)
│   ├── style.css            ← Styling (presentation)
│   └── app.js               ← JavaScript (behaviour)
└── sample-code/
    ├── sample.py            ← Intentionally bad Python code
    └── sample.js            ← Intentionally bad JavaScript
```

---

## Quick Start

### 1. Get an API Key
Sign up at https://console.anthropic.com and create an API key.

### 2. Create .env file
Inside the `backend/` folder, create a file named `.env`:
```
ANTHROPIC_API_KEY=your_actual_key_here
PORT=8000
```

### 3. Set up Python environment
```bash
cd backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 4. Run the server
```bash
python main.py
```

### 5. Open the app
Go to: **http://localhost:8000**
API Docs: **http://localhost:8000/docs**

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/review/` | Week 1: Code quality review |
| POST | `/api/test/` | Week 2: Test generation |
| POST | `/api/audit/` | Week 3: Security audit |
| POST | `/api/document/` | Week 4: Documentation |
| GET | `/health` | Server health check |

All POST endpoints accept: `{ "code": "...", "language": "python" }`

---

## Tech Stack

| Technology | Purpose |
|------------|---------|
| Python 3.10+ | Backend language |
| FastAPI | Web framework (async, auto-docs) |
| Uvicorn | ASGI server |
| httpx | Async HTTP client for Claude API |
| python-dotenv | Load .env variables |
| Pydantic | Request/response validation |
| Anthropic Claude | AI model (claude-opus-4-6) |
| HTML/CSS/JS | Frontend (no framework) |

---

## Team 7
Built as a 4-week project — Autopsy AI
