"""
routes/documenter.py
====================
WEEK 4 FEATURE: Automated Documentation Generator

WHAT THIS FILE DOES:
Reads code and generates two professional documentation files:
  1. README.md     — the public-facing project overview for GitHub
  2. TECHNICAL.md  — deep-dive technical docs for developers

WHY IS DOCUMENTATION IMPORTANT?
"Code is read 10x more often than it is written." — Robert C. Martin
Good documentation lets a new developer contribute in hours, not weeks.
It also shows professionalism when employers look at your GitHub.

WHAT MAKES A GOOD README?
A great README has:
  - Clear title + one-line description
  - What the project does and why it exists
  - How to install and run it (step by step)
  - How to use it (with code examples)
  - Tech stack explanation
  - Contributing guide

WHAT IS DOCSTRING?
A docstring is a string at the start of a function/class explaining
what it does. Python uses triple quotes:
  def add(a, b):
      \"""Returns the sum of a and b.\"""
      return a + b
This module generates these automatically.
"""

import json
import re
from typing import Optional, List
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from ai_helper import call_claude

router = APIRouter()


class CodeFile(BaseModel):
    """Represents one file in a multi-file submission"""
    name: str
    content: str
    language: str = "python"


class DocumentRequest(BaseModel):
    code: Optional[str] = None
    language: Optional[str] = "python"
    files: Optional[List[CodeFile]] = None
    project_name: Optional[str] = None
    project_description: Optional[str] = None


DOCUMENTER_SYSTEM_PROMPT = """You are a Senior Technical Writer with 10 years experience writing
documentation for open-source projects and developer tools.

Generate COMPLETE, PROFESSIONAL documentation for the provided codebase.

README.md must include:
1. # Project Name with a relevant emoji
2. One-line description (what it does + who it's for)
3. ## Features — bullet list with emojis, each feature in plain English
4. ## Tech Stack — table: Technology | Version | Purpose
5. ## Prerequisites — what must be installed first (Python 3.10+, Node.js, etc.)
6. ## Installation — numbered steps, every command in a code block
7. ## Usage — realistic code example with output
8. ## Project Structure — file tree with one-line descriptions
9. ## API Reference — each function: signature, description, params, returns, example
10. ## Contributing — how to fork, branch, PR
11. ## License — MIT License

TECHNICAL_DOCS.md must include:
1. ## Architecture Overview — how the parts connect (2-3 paragraphs)
2. ## Module Documentation — for each file/module:
   - Purpose
   - Dependencies (what it imports)
   - Each function: name, params table, return type, raises, example
3. ## Data Flow — step-by-step what happens when a user submits code
4. ## Design Decisions — WHY key technical choices were made
5. ## Extending the Project — how to add new features

Respond ONLY in this exact JSON format:
{
  "projectName": "Autopsy AI",
  "tagline": "Senior Developer in a Box — AI-powered code review, testing, and security auditing",
  "detectedLanguages": ["Python", "JavaScript"],
  "detectedFrameworks": ["FastAPI", "pytest"],
  "functionCount": 12,
  "lineCount": 340,
  "readme": "# Autopsy AI\\n\\n...complete README content...",
  "technicalDocs": "# Technical Documentation\\n\\n...complete technical docs...",
  "suggestedBadges": [
    "![Python](https://img.shields.io/badge/Python-3.10+-blue)",
    "![FastAPI](https://img.shields.io/badge/FastAPI-0.111-green)"
  ]
}

Make the documentation genuinely excellent — the kind that makes a developer
want to use and contribute to the project immediately.
RESPOND ONLY WITH VALID JSON."""


@router.post("/")
async def generate_documentation(request: DocumentRequest):
    """
    POST /api/document
    Generates README.md and technical documentation for provided code.
    Body: { "code": "...", "language": "python", "project_name": "optional" }
    Returns: JSON with readme and technicalDocs strings
    """
    # Build combined code content from single or multiple files
    if request.files and len(request.files) > 0:
        code_content = "\n\n".join(
            f"### File: {f.name}\n```{f.language}\n{f.content}\n```"
            for f in request.files
        )
    elif request.code:
        code_content = f"```{request.language or 'python'}\n{request.code}\n```"
    else:
        raise HTTPException(status_code=400, detail="No code provided.")

    print(f"[DOCUMENTER] Generating docs for project: {request.project_name or 'unnamed'}")

    hints = []
    if request.project_name:
        hints.append(f"Project name: {request.project_name}")
    if request.project_description:
        hints.append(f"Project description: {request.project_description}")
    hint_text = "\n".join(hints)

    user_message = (
        f"Generate comprehensive documentation for this project.\n"
        f"{hint_text}\n\n"
        f"{code_content}\n\n"
        f"Make the README so good that a developer finding this project on GitHub "
        f"immediately understands what it does and wants to use it."
    )

    try:
        claude_response = await call_claude(DOCUMENTER_SYSTEM_PROMPT, user_message)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    try:
        clean = re.sub(r"```(?:json)?\s*", "", claude_response).replace("```", "").strip()
        result = json.loads(clean)
    except json.JSONDecodeError:
        result = {
            "projectName": request.project_name or "Project",
            "readme": claude_response,
            "technicalDocs": "",
            "rawResponse": True,
        }

    print(f"[DOCUMENTER] Done. Project: {result.get('projectName')}")
    return result
