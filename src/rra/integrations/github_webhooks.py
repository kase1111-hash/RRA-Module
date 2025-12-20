# SPDX-License-Identifier: FSL-1.1-ALv2
# Copyright 2025 Kase Branham
"""
GitHub Webhook Integration for RRA Module.

Provides automated fork detection and derivative tracking:
- GitHub webhook handlers for fork events
- Fork owner notifications
- Derivative registration automation
"""

import hmac
import hashlib
import json
import os
import secrets
from datetime import datetime
from typing import Optional, Dict, Any, List
from pathlib import Path

from pydantic import BaseModel, Field


# =============================================================================
# Configuration
# =============================================================================

GITHUB_WEBHOOK_SECRET = os.environ.get("GITHUB_WEBHOOK_SECRET", "")
GITHUB_API_TOKEN = os.environ.get("GITHUB_API_TOKEN", "")
FORK_DATA_PATH = Path(os.environ.get("RRA_FORK_DATA_PATH", "data/forks.json"))


# =============================================================================
# Models
# =============================================================================

class ForkInfo(BaseModel):
    """Information about a detected fork."""
    parent_repo: str
    parent_url: str
    fork_repo: str
    fork_url: str
    fork_owner: str
    forked_at: str
    detected_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    notified: bool = False
    registered_as_derivative: bool = False
    derivative_ip_asset_id: Optional[str] = None


class ForkEvent(BaseModel):
    """GitHub fork event payload."""
    action: str = "created"
    repository: Dict[str, Any]
    forkee: Dict[str, Any]
    sender: Dict[str, Any]


# =============================================================================
# GitHub Webhook Handler
# =============================================================================

class GitHubWebhookHandler:
    """Handle GitHub webhooks for fork detection."""

    def __init__(self, secret: Optional[str] = None):
        """
        Initialize the webhook handler.

        Args:
            secret: GitHub webhook secret for signature verification
        """
        self.secret = secret or GITHUB_WEBHOOK_SECRET
        self._forks: Dict[str, ForkInfo] = {}
        self._load_forks()

    def _load_forks(self) -> None:
        """Load fork data from storage."""
        if FORK_DATA_PATH.exists():
            try:
                with open(FORK_DATA_PATH, 'r') as f:
                    data = json.load(f)
                    self._forks = {
                        k: ForkInfo(**v) for k, v in data.items()
                    }
            except (json.JSONDecodeError, IOError):
                self._forks = {}

    def _save_forks(self) -> None:
        """Save fork data to storage."""
        FORK_DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(FORK_DATA_PATH, 'w') as f:
            json.dump(
                {k: v.model_dump() for k, v in self._forks.items()},
                f, indent=2, default=str
            )

    def verify_signature(self, payload: bytes, signature: str) -> bool:
        """
        Verify GitHub webhook signature.

        Args:
            payload: Raw request payload bytes
            signature: X-Hub-Signature-256 header value

        Returns:
            True if signature is valid
        """
        if not self.secret:
            return True  # No secret configured, skip verification

        if not signature or not signature.startswith("sha256="):
            return False

        expected = hmac.new(
            self.secret.encode(),
            payload,
            hashlib.sha256
        ).hexdigest()

        return hmac.compare_digest(f"sha256={expected}", signature)

    async def handle_fork_event(self, event: Dict[str, Any]) -> ForkInfo:
        """
        Handle fork creation event.

        Args:
            event: GitHub webhook event payload

        Returns:
            ForkInfo with extracted fork details
        """
        repo_data = event.get('repository', {})
        fork_data = event.get('forkee', {})

        fork_info = ForkInfo(
            parent_repo=repo_data.get('full_name', ''),
            parent_url=repo_data.get('html_url', ''),
            fork_repo=fork_data.get('full_name', ''),
            fork_url=fork_data.get('html_url', ''),
            fork_owner=fork_data.get('owner', {}).get('login', ''),
            forked_at=fork_data.get('created_at', datetime.utcnow().isoformat()),
        )

        # Store fork info
        fork_key = f"{fork_info.fork_repo}"
        self._forks[fork_key] = fork_info
        self._save_forks()

        return fork_info

    def get_fork(self, fork_repo: str) -> Optional[ForkInfo]:
        """Get fork info by repository name."""
        return self._forks.get(fork_repo)

    def get_forks_for_parent(self, parent_repo: str) -> List[ForkInfo]:
        """Get all forks for a parent repository."""
        return [
            fork for fork in self._forks.values()
            if fork.parent_repo == parent_repo
        ]

    def get_all_forks(self) -> List[ForkInfo]:
        """Get all detected forks."""
        return list(self._forks.values())

    def mark_notified(self, fork_repo: str) -> bool:
        """Mark a fork as notified."""
        fork = self._forks.get(fork_repo)
        if fork:
            fork.notified = True
            self._save_forks()
            return True
        return False

    def mark_registered(self, fork_repo: str, ip_asset_id: str) -> bool:
        """Mark a fork as registered as derivative."""
        fork = self._forks.get(fork_repo)
        if fork:
            fork.registered_as_derivative = True
            fork.derivative_ip_asset_id = ip_asset_id
            self._save_forks()
            return True
        return False


# =============================================================================
# Fork Notifier
# =============================================================================

class ForkNotifier:
    """Notify fork owners about derivative registration requirements."""

    def __init__(self, github_token: Optional[str] = None):
        """
        Initialize the notifier.

        Args:
            github_token: GitHub API token for creating issues
        """
        self.github_token = github_token or GITHUB_API_TOKEN

    async def notify_fork_owner(
        self,
        fork_info: ForkInfo,
        ip_asset_id: str,
        royalty_rate: float = 0.05,
    ) -> Dict[str, Any]:
        """
        Send notification to fork owner.

        Creates a GitHub issue on the fork repository informing
        the owner about derivative registration options.

        Args:
            fork_info: Fork information
            ip_asset_id: Parent IP Asset ID on Story Protocol
            royalty_rate: Royalty rate for derivatives

        Returns:
            Notification result
        """
        issue_body = self._generate_notification_body(
            fork_info=fork_info,
            ip_asset_id=ip_asset_id,
            royalty_rate=royalty_rate,
        )

        # If we have a GitHub token, create an issue
        if self.github_token:
            return await self._create_github_issue(
                repo=fork_info.fork_repo,
                title="Derivative Registration Available - RRA",
                body=issue_body,
                labels=["rra", "derivative", "ip-licensing"],
            )

        # Otherwise, just return the notification content
        return {
            "status": "pending",
            "message": "GitHub token not configured, issue not created",
            "notification_content": issue_body,
        }

    def _generate_notification_body(
        self,
        fork_info: ForkInfo,
        ip_asset_id: str,
        royalty_rate: float,
    ) -> str:
        """Generate the notification issue body."""
        royalty_pct = royalty_rate * 100

        return f"""## Fork Detected - Derivative Registration Available

You've forked [{fork_info.parent_repo}]({fork_info.parent_url}), which is registered as an IP Asset on Story Protocol.

### What This Means

- The original repository has on-chain licensing terms
- Derivatives (forks) can be tracked and monetized
- Royalty rate: **{royalty_pct}%** on commercial revenue

### Your Options

**Option 1: Register as Derivative (Recommended)**
- Your fork is recognized on-chain
- You can sell licenses to your fork
- Royalties automatically flow to original creator
- Your work builds on-chain reputation

**Option 2: Non-Commercial Use**
- Keep your fork private or non-commercial
- No registration needed
- No royalty obligations

**Option 3: Negotiate Custom Terms**
- Contact original creator for special terms
- May reduce or eliminate royalties

### Register Your Fork

Using CLI:
```bash
rra register-derivative \\
  --parent {ip_asset_id} \\
  --fork {fork_info.fork_url}
```

Or visit: https://natlangchain.io/register-derivative/{ip_asset_id}

---

*This notification was generated by the [Revenant Repo Agent](https://github.com/natlangchain/rra-module).*
*Questions? Reply to this issue or contact the original repository maintainer.*
"""

    async def _create_github_issue(
        self,
        repo: str,
        title: str,
        body: str,
        labels: List[str],
    ) -> Dict[str, Any]:
        """Create a GitHub issue."""
        import aiohttp

        url = f"https://api.github.com/repos/{repo}/issues"
        headers = {
            "Authorization": f"token {self.github_token}",
            "Accept": "application/vnd.github.v3+json",
        }
        data = {
            "title": title,
            "body": body,
            "labels": labels,
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=data) as response:
                    if response.status == 201:
                        result = await response.json()
                        return {
                            "status": "created",
                            "issue_url": result.get("html_url"),
                            "issue_number": result.get("number"),
                        }
                    else:
                        error_text = await response.text()
                        return {
                            "status": "failed",
                            "error": f"GitHub API returned {response.status}: {error_text}",
                        }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
            }


# =============================================================================
# Fork Tracker
# =============================================================================

class ForkTracker:
    """Track forks and build derivative trees."""

    def __init__(self):
        """Initialize the fork tracker."""
        self.webhook_handler = GitHubWebhookHandler()
        self.notifier = ForkNotifier()

    def get_derivative_tree(
        self,
        parent_repo: str,
        include_unregistered: bool = True,
    ) -> Dict[str, Any]:
        """
        Get the complete derivative tree for a repository.

        Args:
            parent_repo: Parent repository name (owner/repo)
            include_unregistered: Include forks not yet registered

        Returns:
            Derivative tree with statistics
        """
        forks = self.webhook_handler.get_forks_for_parent(parent_repo)

        registered = [f for f in forks if f.registered_as_derivative]
        unregistered = [f for f in forks if not f.registered_as_derivative]

        # Build tree structure
        tree = {
            "root": {
                "repo": parent_repo,
                "type": "original",
            },
            "derivatives": [],
            "stats": {
                "total_forks": len(forks),
                "registered_derivatives": len(registered),
                "pending_registration": len(unregistered),
                "notification_rate": (
                    sum(1 for f in forks if f.notified) / len(forks)
                    if forks else 0
                ),
            },
        }

        # Add registered derivatives
        for fork in registered:
            tree["derivatives"].append({
                "repo": fork.fork_repo,
                "url": fork.fork_url,
                "owner": fork.fork_owner,
                "forked_at": fork.forked_at,
                "ip_asset_id": fork.derivative_ip_asset_id,
                "type": "registered_derivative",
            })

        # Add unregistered if requested
        if include_unregistered:
            for fork in unregistered:
                tree["derivatives"].append({
                    "repo": fork.fork_repo,
                    "url": fork.fork_url,
                    "owner": fork.fork_owner,
                    "forked_at": fork.forked_at,
                    "notified": fork.notified,
                    "type": "unregistered_fork",
                })

        return tree

    def get_fork_stats(self) -> Dict[str, Any]:
        """Get overall fork tracking statistics."""
        all_forks = self.webhook_handler.get_all_forks()

        return {
            "total_forks_detected": len(all_forks),
            "total_notified": sum(1 for f in all_forks if f.notified),
            "total_registered": sum(1 for f in all_forks if f.registered_as_derivative),
            "registration_rate": (
                sum(1 for f in all_forks if f.registered_as_derivative) / len(all_forks)
                if all_forks else 0
            ),
            "unique_parent_repos": len(set(f.parent_repo for f in all_forks)),
        }


# =============================================================================
# RRA Registration Checker
# =============================================================================

class RRARegistrationChecker:
    """Check if repositories are registered with RRA."""

    def __init__(self, registrations_path: Path = None):
        """Initialize the registration checker."""
        self.registrations_path = registrations_path or Path("data/rra_registrations.json")
        self._registrations: Dict[str, Dict[str, Any]] = {}
        self._load_registrations()

    def _load_registrations(self) -> None:
        """Load registration data."""
        if self.registrations_path.exists():
            try:
                with open(self.registrations_path, 'r') as f:
                    self._registrations = json.load(f)
            except (json.JSONDecodeError, IOError):
                self._registrations = {}

    def _save_registrations(self) -> None:
        """Save registration data."""
        self.registrations_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.registrations_path, 'w') as f:
            json.dump(self._registrations, f, indent=2, default=str)

    def is_registered(self, repo: str) -> bool:
        """Check if a repository is registered with RRA."""
        return repo in self._registrations

    def get_registration(self, repo: str) -> Optional[Dict[str, Any]]:
        """Get registration details for a repository."""
        return self._registrations.get(repo)

    def register(
        self,
        repo: str,
        ip_asset_id: str,
        royalty_rate: float = 0.05,
        owner_address: str = None,
    ) -> Dict[str, Any]:
        """Register a repository with RRA."""
        registration = {
            "repo": repo,
            "ip_asset_id": ip_asset_id,
            "royalty_rate": royalty_rate,
            "owner_address": owner_address,
            "registered_at": datetime.utcnow().isoformat(),
        }
        self._registrations[repo] = registration
        self._save_registrations()
        return registration


# =============================================================================
# Global Instances
# =============================================================================

webhook_handler = GitHubWebhookHandler()
fork_notifier = ForkNotifier()
fork_tracker = ForkTracker()
registration_checker = RRARegistrationChecker()
