"""
main.py
=======
THE ENTRY POINT — This is the first file Python runs.

WHAT IS FASTAPI?
FastAPI is a modern Python web framework for building APIs.
It's based on Starlette (ASGI framework) and uses Python type hints.

Key advantages over Flask:
  1. ASYNC — handles many requests simultaneously without blocking
  2. AUTO DOCS — visit /docs to get interactive API documentation FREE
  3. VALIDATION — Pydantic models auto-validate all input/output
  4. FAST — one of the fastest Python frameworks (hence "Fast")

WHAT IS ASGI?
ASGI (Asynchronous Server Gateway Interface) is how Python web apps
communicate with web servers. FastAPI uses Uvicorn as its ASGI server.
Think: Uvicorn is the engine, FastAPI is the car body.

WHAT IS CORS?
CORS (Cross-Origin Resource Sharing) is a browser security feature.
By default, browsers BLOCK JavaScript from calling APIs on different domains.
Example: our frontend at localhost:8000 wants to call an API at localhost:8001
Without CORS headers, the browser refuses this call.
CORSMiddleware adds the right headers so the browser allows it.

HOW ROUTING WORKS:
  main.py registers each router with a prefix:
    app.include_router(reviewer_router, prefix="/api/review")
  
  reviewer.py defines its endpoint as @router.post("/")
  
  Combined → POST /api/review/   calls reviewer.py's function
  
  So the full request path is:
  Browser → POST http://localhost:8000/api/review/
          → FastAPI matches prefix /api/review
          → reviewer_router handles it
          → review_code() function runs
          → Response returns to browser

HOW TO RUN:
  python main.py              ← runs the server directly
  uvicorn main:app --reload   ← runs with auto-reload on file changes (development)
"""

import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from dotenv import load_dotenv

# Load .env file FIRST — before any other imports that need env vars
load_dotenv()

# Import our route modules
# Each module defines its own APIRouter with endpoints
from routes.reviewer   import router as reviewer_router
from routes.tester     import router as tester_router
from routes.bug_hunter import router as bug_hunter_router
from routes.documenter import router as documenter_router
from ai_helper import get_runtime_ai_config

# ─────────────────────────────────────────────────────────────────────────────
# CREATE THE FASTAPI APPLICATION
# title, description, version appear in the /docs page
# ─────────────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="Autopsy AI",
    description=(
        "Senior Developer in a Box.\n\n"
        "An AI-powered platform for automated code review, test generation, "
        "security auditing, and documentation — like CodeRabbit, but yours.\n\n"
        "Built with FastAPI + Anthropic Claude API."
    ),
    version="1.0.0",
    docs_url="/docs",       # Interactive API docs at http://localhost:8000/docs
    redoc_url="/redoc",     # Alternative docs at http://localhost:8000/redoc
)

# ─────────────────────────────────────────────────────────────────────────────
# CORS MIDDLEWARE
# This MUST be added before routes.
# allow_origins=["*"] allows any domain — fine for development.
# In production, replace with your actual frontend domain:
#   allow_origins=["https://yourdomain.com"]
# ─────────────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

# ─────────────────────────────────────────────────────────────────────────────
# REGISTER API ROUTES
# Each router handles a group of endpoints.
# prefix="/api/review" means all routes inside reviewer.py
# get the /api/review prefix prepended to their paths.
# tags=["..."] groups them nicely in the /docs page.
# ─────────────────────────────────────────────────────────────────────────────
app.include_router(
    reviewer_router,
    prefix="/api/review",
    tags=["Week 1 — Code Review"]
)
app.include_router(
    tester_router,
    prefix="/api/test",
    tags=["Week 2 — Test Generation"]
)
app.include_router(
    bug_hunter_router,
    prefix="/api/audit",
    tags=["Week 3 — Security Audit"]
)
app.include_router(
    documenter_router,
    prefix="/api/document",
    tags=["Week 4 — Documentation"]
)

# ─────────────────────────────────────────────────────────────────────────────
# SERVE FRONTEND STATIC FILES
# This makes FastAPI serve the HTML/CSS/JS files from the frontend/ folder.
# So you only need to run ONE server (not a separate frontend server).
# Visit http://localhost:8000 to see the frontend.
# ─────────────────────────────────────────────────────────────────────────────
FRONTEND_DIR = Path(__file__).parent.parent / "frontend"

if FRONTEND_DIR.exists():
    # Mount /static to serve CSS, JS, images etc.
    app.mount(
        "/static",
        StaticFiles(directory=str(FRONTEND_DIR)),
        name="static"
    )

    @app.get("/", include_in_schema=False)
    async def serve_index():
        """Serve the main HTML file at the root URL"""
        index_path = FRONTEND_DIR / "index.html"
        if index_path.exists():
            return FileResponse(str(index_path))
        return JSONResponse({"message": "Frontend not found. Place index.html in frontend/ folder."})

# ─────────────────────────────────────────────────────────────────────────────
# HEALTH CHECK ENDPOINT
# Good practice: always have a /health endpoint.
# Used by monitoring tools, Docker health checks, load balancers.
# Visit: http://localhost:8000/health
# ─────────────────────────────────────────────────────────────────────────────
@app.get("/health", tags=["System"])
async def health_check():
    """Returns server status. Useful for monitoring."""
    ai_config = get_runtime_ai_config()
    return {
        "status": "healthy",
        "message": "Autopsy AI is running!",
        "api_key_configured": ai_config["api_key_configured"],
        "ai_provider": ai_config["provider"],
        "ai_model": ai_config["model"],
        "configured_key_count": ai_config["configured_key_count"],
        "docs": "http://localhost:8000/docs",
        "endpoints": {
            "review":   "POST /api/review/",
            "test":     "POST /api/test/",
            "audit":    "POST /api/audit/",
            "document": "POST /api/document/",
        }
    }

# ─────────────────────────────────────────────────────────────────────────────
# STARTUP / SHUTDOWN EVENTS
# Code that runs once when the server starts or stops.
# ─────────────────────────────────────────────────────────────────────────────
@app.on_event("startup")
async def on_startup():
    """Runs once when the server starts up"""
    ai_config = get_runtime_ai_config()
    print("\n" + "="*55)
    print("  🔬  Autopsy AI — Senior Developer in a Box")
    print("="*55)
    print(f"  Server:   http://localhost:{os.getenv('PORT', 8000)}")
    print(f"  API Docs: http://localhost:{os.getenv('PORT', 8000)}/docs")
    print(f"  AI Model: {ai_config['model']}")
    if not ai_config["api_key_configured"]:
        print("  ⚠️  WARNING: No Anthropic API key set in .env file!")
        print("     Add ANTHROPIC_API_KEY=your_key or ANTHROPIC_API_KEYS=key1,key2")
    else:
        print(f"  ✅  Anthropic keys configured: {ai_config['configured_key_count']}")
    print("="*55 + "\n")


# ─────────────────────────────────────────────────────────────────────────────
# RUN THE SERVER
# This block only runs when you do: python main.py
# (Not when imported as a module)
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=True,       # Auto-restart when you save any Python file
        reload_dirs=["."], # Watch this directory for changes
    )
