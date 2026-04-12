# -*- coding: utf-8 -*-
"""GitHub webhooks: receive push/PR events and record them for analysis tracking."""

import hmac
import hashlib
import os
import json
from datetime import datetime
from fastapi import APIRouter, HTTPException, Request, Header
from pydantic import BaseModel, Field
from typing import List, Optional

router = APIRouter()

analysis_history: List[dict] = []


class WebhookStatus(BaseModel):
    id: str
    repo: str
    branch: str
    event: str
    status: str
    timestamp: str
    results_summary: Optional[dict] = None


def verify_github_signature(payload: bytes, signature: str, secret: str) -> bool:
    """Verify the webhook payload was sent by GitHub using HMAC."""
    if not secret:
        return True
    expected = "sha256=" + hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


@router.post("/github")
async def github_webhook(request: Request, x_hub_signature_256: Optional[str] = Header(None)):
    """Receive GitHub webhook events (push, pull_request)."""
    body = await request.body()
    secret = os.getenv("GITHUB_WEBHOOK_SECRET", "")

    if secret and x_hub_signature_256:
        if not verify_github_signature(body, x_hub_signature_256, secret):
            raise HTTPException(status_code=401, detail="Invalid webhook signature")

    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    event_type = request.headers.get("X-GitHub-Event", "unknown")

    if event_type == "ping":
        return {"status": "pong", "message": "Webhook configured successfully"}

    repo_name = payload.get("repository", {}).get("full_name", "unknown")
    timestamp = datetime.utcnow().isoformat()

    if event_type == "push":
        branch = payload.get("ref", "").replace("refs/heads/", "")
        commits = payload.get("commits", [])

        entry = {
            "id": f"push-{timestamp}",
            "repo": repo_name,
            "branch": branch,
            "event": "push",
            "status": "received",
            "timestamp": timestamp,
            "details": {
                "commits": len(commits),
                "pusher": payload.get("pusher", {}).get("name", "unknown"),
                "commit_messages": [c.get("message", "") for c in commits[:5]],
            },
        }
        analysis_history.append(entry)

        return {
            "status": "accepted",
            "event": "push",
            "repo": repo_name,
            "branch": branch,
            "message": f"Push event received. {len(commits)} commit(s) on {branch}.",
            "analysis_id": entry["id"],
        }

    elif event_type == "pull_request":
        action = payload.get("action", "")
        pr = payload.get("pull_request", {})
        pr_number = pr.get("number", 0)
        head_branch = pr.get("head", {}).get("ref", "")
        base_branch = pr.get("base", {}).get("ref", "")

        if action not in ("opened", "synchronize", "reopened"):
            return {"status": "skipped", "reason": f"PR action '{action}' does not trigger analysis"}

        entry = {
            "id": f"pr-{pr_number}-{timestamp}",
            "repo": repo_name,
            "branch": head_branch,
            "event": f"pull_request:{action}",
            "status": "received",
            "timestamp": timestamp,
            "details": {
                "pr_number": pr_number,
                "title": pr.get("title", ""),
                "head": head_branch,
                "base": base_branch,
                "author": pr.get("user", {}).get("login", "unknown"),
            },
        }
        analysis_history.append(entry)

        return {
            "status": "accepted",
            "event": "pull_request",
            "action": action,
            "repo": repo_name,
            "pr_number": pr_number,
            "branches": {"head": head_branch, "base": base_branch},
            "message": f"PR #{pr_number} ({action}) received. Analysis queued.",
            "analysis_id": entry["id"],
        }

    return {"status": "ignored", "event": event_type, "message": f"Event type '{event_type}' not handled"}


@router.get("/history")
async def get_webhook_history():
    """Return recent webhook events and their analysis status."""
    return {
        "total": len(analysis_history),
        "events": analysis_history[-50:],
    }


@router.get("/status/{analysis_id}")
async def get_analysis_status(analysis_id: str):
    """Check the status of a specific analysis triggered by webhook."""
    for entry in analysis_history:
        if entry["id"] == analysis_id:
            return entry
    raise HTTPException(status_code=404, detail=f"Analysis {analysis_id} not found")
