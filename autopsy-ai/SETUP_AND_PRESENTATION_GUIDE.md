# 🔬 Autopsy AI — Complete Setup & Presentation Guide
### Team 7 | Everything you need to build, run, and explain this project

---

## PART 1: CREATE ALL FILES MANUALLY (Step by Step)

Follow this EXACTLY. Create each file and folder in order.

---

### STEP 1 — Create the main project folder

Open **File Explorer** (Windows) or **Finder** (Mac).
Navigate to your Desktop or Documents.
Create a new folder named: `autopsy-ai`

Inside `autopsy-ai`, create two more folders:
- `backend`
- `frontend`
- `sample-code`

Inside `backend`, create one more folder:
- `routes`

Your folder tree should look like this:
```
autopsy-ai/
├── backend/
│   └── routes/
├── frontend/
└── sample-code/
```

---

### STEP 2 — Create backend files

**File 1: `backend/requirements.txt`**
Open Notepad (Windows) or TextEdit (Mac).
Paste the content. Save as `requirements.txt` inside the `backend` folder.

```
fastapi==0.111.0
uvicorn[standard]==0.29.0
httpx==0.27.0
python-dotenv==1.0.1
pydantic==2.7.1
python-multipart==0.0.9
```

WHY EACH PACKAGE:
- `fastapi`       → Our web framework. Like Django but faster and async.
- `uvicorn`       → The server that runs FastAPI. Like Apache but for Python async.
- `httpx`         → Makes HTTP calls to Claude API. Like requests but async.
- `python-dotenv` → Reads .env file so we don't hardcode API keys.
- `pydantic`      → Validates incoming JSON automatically. Part of FastAPI.
- `python-multipart` → Needed for file uploads (future feature).

---

**File 2: `backend/.env`**
Create a new file named `.env` (just `.env`, nothing before the dot).
Add this content — replace with your real API key:

```
ANTHROPIC_API_KEY=your_actual_api_key_here
PORT=8000
```

Get your API key at: https://console.anthropic.com
Click "Create Key" → Copy it → Paste it here.

⚠️ IMPORTANT: NEVER share this file. NEVER upload it to GitHub.
The `.gitignore` file prevents this accidentally.

---

**File 3: `backend/.gitignore`**
Create a file named `.gitignore` inside `backend/`.

```
venv/
__pycache__/
*.pyc
*.pyo
.env
*.log
.DS_Store
```

WHY: Git is version control. `.gitignore` tells Git which files to IGNORE.
We ignore `venv/` (huge, regeneratable) and `.env` (contains secrets).

---

**File 4: `backend/routes/__init__.py`**
Create a file named `__init__.py` inside `backend/routes/`.
Leave it completely EMPTY (or add a comment).

WHY: Python uses this file to recognize `routes/` as a "package"
(a folder that can be imported). Without it, `from routes.reviewer import router`
would give a ModuleNotFoundError.

---

Now create these files using the code from the main project guide:
- `backend/ai_helper.py`
- `backend/main.py`
- `backend/routes/reviewer.py`
- `backend/routes/tester.py`
- `backend/routes/bug_hunter.py`
- `backend/routes/documenter.py`
- `frontend/index.html`
- `frontend/style.css`
- `frontend/app.js`
- `sample-code/sample.py`
- `sample-code/sample.js`

---

### STEP 3 — Install Python

Download Python 3.10 or newer from: https://python.org/downloads/
During installation: ✅ CHECK "Add Python to PATH"

Verify in terminal:
```bash
python --version
# Should show: Python 3.10.x or newer
```

---

### STEP 4 — Open terminal in backend folder

**Windows:** Open the `backend` folder → Shift + Right Click → "Open PowerShell here"
**Mac:** Open Terminal → type `cd ` → drag the backend folder → press Enter

---

### STEP 5 — Create Virtual Environment

```bash
python -m venv venv
```

WHY VIRTUAL ENVIRONMENT?
Think of it as an isolated bubble. Packages installed here don't affect
any other Python project on your computer. It prevents version conflicts.

Activate it:
```bash
# Mac/Linux:
source venv/bin/activate

# Windows:
venv\Scripts\activate
```

You'll see `(venv)` at the start of your terminal line. ✅

---

### STEP 6 — Install packages

```bash
pip install -r requirements.txt
```

This reads `requirements.txt` and installs all 6 packages.
Takes 1-2 minutes. You'll see a progress bar for each package.

---

### STEP 7 — Run the server

```bash
python main.py
```

You should see:
```
=======================================================
  🔬  Autopsy AI — Senior Developer in a Box
=======================================================
  Server:   http://localhost:8000
  API Docs: http://localhost:8000/docs
  ✅  Claude API key loaded (sk-ant-...)
=======================================================
```

If you see `⚠️ WARNING: ANTHROPIC_API_KEY not set` → check your `.env` file.

---

### STEP 8 — Open the app

Open your browser and go to: **http://localhost:8000**

Also check: **http://localhost:8000/docs**
This is the auto-generated API documentation — a free feature of FastAPI!
You can test every endpoint directly from the browser here.

---

## PART 2: HOW THE CODE WORKS (Explanation for Presentations)

---

### What happens when user clicks "Run Analysis"?

```
User clicks button
       ↓
app.js: runAnalysis() runs
       ↓
fetch('http://localhost:8000/api/review/', {
  method: 'POST',
  body: JSON.stringify({ code: "...", language: "python" })
})
       ↓
FastAPI receives the request at /api/review/
       ↓
Pydantic validates: is 'code' a string? is it present?
       ↓
reviewer.py: review_code() function runs
       ↓
ai_helper.py: call_claude(system_prompt, user_code)
       ↓
httpx sends POST to https://api.anthropic.com/v1/messages
       ↓
Claude API processes the request (2-10 seconds)
       ↓
Claude returns JSON response
       ↓
reviewer.py parses the JSON, returns it to FastAPI
       ↓
FastAPI sends JSON response back to the browser
       ↓
app.js: renderReview(data) builds the HTML results UI
       ↓
User sees the results! ✅
```

---

### Why FastAPI over Flask?

| Feature | Flask | FastAPI |
|---------|-------|---------|
| Speed | Medium | Very Fast (async) |
| Auto Docs | ❌ Manual | ✅ Built-in at /docs |
| Validation | Manual | ✅ Pydantic automatic |
| Async support | Limited | ✅ Native |
| Type hints | Optional | ✅ Used everywhere |
| Learning curve | Easy | Easy |

FastAPI is now used by Microsoft, Netflix, and Uber in production.

---

### What is a System Prompt? (Prompt Engineering)

When we call Claude, we send TWO things:

**1. System Prompt** (the "job description"):
```python
"You are a Senior Software Engineer performing a code review.
Analyze for: Long Functions, Unused Variables, DRY violations...
Respond ONLY with valid JSON in this format: {...}"
```

**2. User Message** (the actual work):
```python
"Please review this python code:
```python
def do_everything(data):
    ...
```"
```

The system prompt stays the same for every request.
The user message changes with each new piece of code.

**Why force JSON output?**
If we ask Claude to respond in plain text, we'd get:
"The code has 3 issues. First, the function is too long..."
→ Hard to display in a structured UI.

If we force JSON, we get:
```json
{"score": 65, "issues": [{"type": "Long Function", "severity": "warning"}]}
```
→ Easy to loop through and build the UI dynamically.

---

### What is the Static Security Scan? (bug_hunter.py)

Before calling Claude (which takes 5-10 seconds), we run instant regex checks:

```python
# This finds "API_KEY = 'something'" in under 1 millisecond
pattern = r'(?i)\bapi[_-]?key\s*=\s*["\'][^"\']{8,}["\']'
match = re.search(pattern, code)
```

**Two-pass architecture:**
```
Pass 1: Regex scan (instant, 0ms)
        → Finds obvious patterns: hardcoded passwords, eval(), etc.
        
Pass 2: Claude AI scan (5-10 seconds)
        → Understands context, traces data flow, finds subtle issues
        → Gets the static findings as context to avoid duplication
```

WHY TWO PASSES?
- Static scan gives instant feedback while AI is thinking
- AI catches what regex can't (context-dependent vulnerabilities)
- Combined = more complete than either alone

---

### What is DRY? (Don't Repeat Yourself)

```python
# BAD — same logic 3 times
total1 = 0
for item in result: total1 += item

total2 = 0
for item in result: total2 += item

total3 = 0
for item in result: total3 += item

# GOOD — written once, called 3 times
def sum_list(items):
    return sum(items)

total1 = sum_list(result)
total2 = sum_list(result)
total3 = sum_list(result)
```

Why does DRY matter?
If the logic needs to change, you change it in ONE place, not 3.
Violating DRY is the #1 source of "I fixed it here but forgot to fix it there" bugs.

---

### What is SQL Injection? (Most Important Security Concept)

```python
# BAD — NEVER do this
user_input = input("Enter username: ")
query = "SELECT * FROM users WHERE name = '" + user_input + "'"
```

If the user types: `' OR '1'='1'; DROP TABLE users; --`
The query becomes:
```sql
SELECT * FROM users WHERE name = '' OR '1'='1'; DROP TABLE users; --'
```
Result: Returns ALL users AND deletes the entire users table.

```python
# GOOD — parameterized queries
cursor.execute("SELECT * FROM users WHERE name = %s", (user_input,))
```
Now the input is treated as DATA, not as SQL CODE. Safe! ✅

This is the #1 web vulnerability (OWASP A03) and has caused some of the
biggest data breaches in history (LinkedIn 2012, Yahoo 2016, etc.)

---

### What is OWASP Top 10?

The Open Web Application Security Project publishes a list of the
10 most critical web security risks every few years:

| # | Risk | Example |
|---|------|---------|
| A01 | Broken Access Control | User can see other users' data |
| A02 | Cryptographic Failures | Passwords stored as MD5 |
| A03 | Injection | SQL Injection, Command Injection |
| A04 | Insecure Design | No rate limiting on login |
| A05 | Security Misconfiguration | Debug mode on in production |
| A06 | Vulnerable Components | Using outdated libraries |
| A07 | Auth Failures | Hardcoded passwords |
| A08 | Integrity Failures | eval(), pickle.loads() |
| A09 | Logging Failures | No audit trail |
| A10 | SSRF | Unvalidated external URLs |

Our Week 3 bug_hunter scans for all 10.

---

### What is AST? (For Week 1 explanation)

AST = Abstract Syntax Tree. It's how compilers understand code structure.

When Python reads this:
```python
def add(a, b):
    return a + b
```

It creates a tree in memory:
```
Module
└── FunctionDef (name="add")
    ├── arguments: [a, b]
    └── Return
        └── BinOp
            ├── Name (id="a")
            ├── Add
            └── Name (id="b")
```

Tools like pylint and flake8 use AST to find unused variables
(a Name node that's never referenced), long functions (count child nodes), etc.

Our tool uses Claude AI instead — Claude understands context and intent
better than pure AST analysis. But knowing what AST is shows deep understanding.

---

### What is async/await? (Backend concept)

Traditional (synchronous) server:
```python
def handle_request():
    result = call_claude()  # BLOCKS — server does nothing for 8 seconds
    return result
# During those 8 seconds, ALL other requests queue up and wait
```

Async server (what FastAPI uses):
```python
async def handle_request():
    result = await call_claude()  # Non-blocking — server handles other requests
    return result
# During the 8 seconds, FastAPI handles 100 other requests freely
```

This is why FastAPI is fast — it can serve many users simultaneously
even while waiting for Claude's slow responses.

---

## PART 3: TEAM TASK BREAKDOWN

### Member 1 — Backend Lead
- Create virtual environment, install packages
- Write `main.py` and `ai_helper.py`
- Register all 4 routers in `main.py`
- Test the /health endpoint
- Fix any import errors

### Member 2 — AI Prompt Engineer (Most Creative Role)
- Write and fine-tune system prompts in all 4 route files
- Test different prompt wordings, see which gives better JSON output
- Ensure JSON format is consistent and parseable
- Add the `re.sub()` cleanup for markdown code fences

### Member 3 — Frontend Developer
- Build `index.html` structure (sidebar, editor, results panels)
- Write `style.css` (dark theme, cards, badges, animations)
- Connect UI to API in `app.js` (fetch calls, render functions)

### Member 4 — QA & Testing
- Write the sample bad code files (sample.py, sample.js)
- Test each endpoint manually and via /docs
- Verify edge cases: empty code, very large code, non-Python code
- Write test report documenting what works and what needs fixing

### Member 5 — DevOps & Documentation
- Set up GitHub repository
- Write .gitignore properly
- Keep README.md updated
- Write the final project report / presentation slides
- Record the demo video

---

## PART 4: PRESENTATION SCRIPT (What to Say)

### Opening (30 seconds):
"Code reviews are the biggest bottleneck in software development.
Senior developers spend 30% of their time reviewing junior code that
an AI could catch in seconds. Autopsy AI is our solution —
a Senior Developer in a Box that reviews, tests, audits, and documents
your code automatically."

### Tech Explanation (1 minute):
"The backend is built with FastAPI, a modern Python framework that gives
us async request handling and auto-generated API documentation.
We use Anthropic's Claude API as our AI brain. Each feature is a separate
route file — reviewer.py, tester.py, bug_hunter.py, documenter.py —
all sharing a common ai_helper.py that handles Claude communication.
The frontend is vanilla HTML, CSS, and JavaScript — no frameworks,
keeping it simple and fast."

### Demo Script (2 minutes):
1. Show the empty state — "Here's Autopsy AI"
2. Load Python sample — "This is intentionally bad code"
3. Run Code Review — "It found [N] issues, gave a score of [X]/100"
4. Point to one issue — "Look — it found the unused variable on line 8
   AND tells us how to fix it"
5. Switch to Security Audit — "Now it runs an OWASP scan"
6. Point to SQL injection — "It found SQL injection AND explained the attack scenario"
7. Show /docs — "FastAPI gives us interactive docs for FREE — we can test
   every endpoint here without any extra tools"

### Key Technical Points to Mention:
- "We use async/await throughout — the server never blocks"
- "Pydantic validates every request automatically — no manual if-checks"
- "The security scanner runs in TWO passes — instant regex first, then AI"
- "We engineered the prompts to always return structured JSON — this is called prompt engineering"
- "The frontend uses the Fetch API with async/await to call our backend"

---

## PART 5: COMMON QUESTIONS & ANSWERS

**Q: What if Claude returns invalid JSON?**
A: We have a try/except block that catches JSONDecodeError and returns
a fallback response so the app never crashes.

**Q: How do you handle large files?**
A: We validate input size (max 60,000 characters) before sending to Claude.

**Q: Is it secure?**
A: For a hackathon project, yes. In production we'd add authentication,
rate limiting, HTTPS, and move the API key to a secrets manager.

**Q: Why not use OpenAI instead of Claude?**
A: Claude has a larger context window (200k tokens) which is better for
analyzing large code files. Also, Claude's instruction-following is better
for returning consistent JSON output.

**Q: What's the difference between static analysis and AI analysis?**
A: Static analysis uses pattern matching (regex) — fast but dumb.
AI analysis understands context and intent — slower but smarter.
We use both together for the best results.

**Q: How long does an analysis take?**
A: Static scan: <1ms. Claude AI: 5-15 seconds depending on code size.

---

*Autopsy AI — Team 7 | Built with FastAPI + Claude AI*
