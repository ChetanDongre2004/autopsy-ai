# -*- coding: utf-8 -*-
"""API routes for generating README and technical documentation from code."""

import json
from typing import Optional, List
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from ai_helper import call_ai
from utils.parsers import clean_ai_json

router = APIRouter()


class CodeFile(BaseModel):
    """One file in a multi-file documentation request."""

    name: str
    content: str
    language: str = "python"


class DocumentRequest(BaseModel):
    """Request body for documentation generation."""

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
    """Generate README and technical documentation for submitted code."""

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
        ai_response = await call_ai(DOCUMENTER_SYSTEM_PROMPT, user_message)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    try:
        result = clean_ai_json(ai_response)
    except json.JSONDecodeError:
        result = {
            "projectName": request.project_name or "Project",
            "readme": ai_response,
            "technicalDocs": "",
            "rawResponse": True,
        }

    print(f"[DOCUMENTER] Done. Project: {result.get('projectName')}")
    return result
