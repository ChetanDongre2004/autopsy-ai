# -*- coding: utf-8 -*-
"""Autopsy AI - FastAPI application entry point."""

import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from dotenv import load_dotenv

load_dotenv()

from routes.reviewer import router as reviewer_router
from routes.tester import router as tester_router
from routes.bug_hunter import router as bug_hunter_router
from routes.documenter import router as documenter_router
from routes.repo_analyzer import router as repo_analyzer_router
from routes.dependency_scanner import router as dependency_router
from routes.branch_comparator import router as branch_comparator_router
from routes.dashboard import router as dashboard_router
from routes.webhook import router as webhook_router
from routes.repo_qa_scanner import router as qa_scanner_router
from routes.dast_simulator import router as dast_router
from routes.code_analyzer import router as code_analyzer_router
from routes.package_checker import router as package_checker_router
from routes.pr_integration import router as pr_router
from routes.report_export import router as report_router
from ai_helper import get_runtime_ai_config


@asynccontextmanager
async def lifespan(app: FastAPI):
    ai = get_runtime_ai_config()
    port = os.getenv("PORT", 8000)
    print(f"\n{'=' * 50}")
    print("  Autopsy AI")
    print(f"{'=' * 50}")
    print(f"  Server:   http://localhost:{port}")
    print(f"  Docs:     http://localhost:{port}/docs")
    print(f"  Provider: {ai['provider']} ({ai['model']})")
    if not ai["api_key_configured"]:
        print("  WARNING: No API key configured in .env")
    print(f"{'=' * 50}\n")
    yield


app = FastAPI(
    title="Autopsy AI",
    description="AI-powered code review, testing, security auditing, and documentation platform.",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

# API Routes
app.include_router(reviewer_router, prefix="/api/review", tags=["Code Review"])
app.include_router(tester_router, prefix="/api/test", tags=["Test Generation"])
app.include_router(bug_hunter_router, prefix="/api/audit", tags=["Security Audit"])
app.include_router(documenter_router, prefix="/api/document", tags=["Documentation"])
app.include_router(repo_analyzer_router, prefix="/api/repo", tags=["Repo Intelligence"])
app.include_router(dependency_router, prefix="/api/dependencies", tags=["Dependency Scanner"])
app.include_router(branch_comparator_router, prefix="/api/branch", tags=["Branch Comparison"])
app.include_router(dashboard_router, prefix="/api/dashboard", tags=["Health Dashboard"])
app.include_router(webhook_router, prefix="/api/webhook", tags=["Automation"])
app.include_router(qa_scanner_router, prefix="/api/qa", tags=["QA Scanner"])
app.include_router(dast_router, prefix="/api/dast", tags=["DAST Simulator"])
app.include_router(code_analyzer_router, prefix="/api/analyze", tags=["Code Analysis"])
app.include_router(package_checker_router, prefix="/api/packages", tags=["Package Checker"])
app.include_router(pr_router, prefix="/api/pr", tags=["PR Integration"])
app.include_router(report_router, prefix="/api/report", tags=["Report Export"])

# Serve frontend
FRONTEND_DIR = Path(__file__).parent.parent / "frontend"

if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")

    @app.get("/", include_in_schema=False)
    async def serve_index():
        index_path = FRONTEND_DIR / "index.html"
        if index_path.exists():
            return FileResponse(str(index_path))
        return JSONResponse({"message": "Frontend not found"})


@app.get("/health", tags=["System"])
async def health_check():
    """Server status and configuration overview."""
    ai = get_runtime_ai_config()
    return {
        "status": "healthy",
        "ai_provider": ai["provider"],
        "ai_model": ai["model"],
        "api_key_configured": ai["api_key_configured"],
        "endpoints": {
            "review": "POST /api/review/",
            "test": "POST /api/test/",
            "audit": "POST /api/audit/",
            "document": "POST /api/document/",
            "repo_analyze": "POST /api/repo/analyze",
            "dependencies": "POST /api/dependencies/scan",
            "branch_diff": "POST /api/branch/compare",
            "dashboard": "POST /api/dashboard/generate",
            "webhook": "POST /api/webhook/github",
            "qa_scan": "POST /api/qa/scan",
            "dast_scan": "POST /api/dast/scan",
            "code_analysis": "POST /api/analyze/full-analysis",
            "packages": "POST /api/packages/check",
            "pr_comment": "POST /api/pr/comment",
            "report": "POST /api/report/html",
        },
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8000)),
        reload=True,
        reload_dirs=["."],
    )
