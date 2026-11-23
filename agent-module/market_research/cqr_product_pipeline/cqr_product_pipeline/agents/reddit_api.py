"""Reddit threads through the official API (app-only OAuth, read only).

Reddit refuses unauthenticated page fetches, so the evidence pack used to keep only the
search snippet of a Reddit hit. With an API app registered this module searches Reddit
for review threads and reads a thread's post and top comments, so consumer complaints
come from what people wrote rather than from a 2-line snippet.

Off by default: it runs only when credentials are configured, from the environment

- ``REDDIT_CLIENT_ID`` / ``REDDIT_CLIENT_SECRET`` (a "script" app at reddit.com/prefs/apps)
- ``REDDIT_USER_AGENT`` (optional; Reddit asks for ``platform:app-id:version (by /u/name)``)

or from a JSON file named by ``CQR_REDDIT_CREDENTIALS`` with the keys ``client_id``,
``client_secret`` and ``user_agent``. Keep that file out of git (a vault folder).

Calls are spaced (``CALL_SPACING``) and capped per run (``MAX_CALLS``) to stay well under
the free tier's rate limit. Every call that fails is recorded; nothing is retried in a loop.
"""

from __future__ import annotations

import base64
import json
import os
import re
import threading
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

TOKEN_URL = "https://www.reddit.com/api/v1/access_token"
API_ROOT = "https://oauth.reddit.com"
WEB_ROOT = "https://www.reddit.com"
DEFAULT_USER_AGENT = "python:cqr-market-research:0.1 (personal research script)"
CALL_SPACING = 1.0  # seconds between API calls
MAX_CALLS = 20  # per run: searches + threads
TIMEOUT = 10
COMMENTS_PER_THREAD = 30
MIN_COMMENT_CHARS = 40
_SKIP_AUTHORS = frozenset({"AutoModerator", "[deleted]"})
_SKIP_BODIES = frozenset({"[deleted]", "[removed]"})
_POST_ID_RE = re.compile(r"/comments/([0-9a-z]{5,8})(?:/|$)", re.IGNORECASE)


def post_id(url: str) -> str:
    """Base-36 post id of a Reddit thread URL ('' when the URL is not a thread)."""
    match = _POST_ID_RE.search(urllib.parse.urlsplit(url or "").path)
    return match.group(1).lower() if match else ""


def _day(created_utc: object) -> str:
    try:
        return datetime.fromtimestamp(float(created_utc), tz=timezone.utc).strftime("%Y-%m-%d")
    except (TypeError, ValueError, OverflowError, OSError):
        return ""


def _one_line(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "")).strip()


@dataclass
class RedditClient:
    client_id: str
    client_secret: str
    user_agent: str = DEFAULT_USER_AGENT
    calls: int = 0
    errors: list[str] = field(default_factory=list)
    _token: str = ""
    _token_until: float = 0.0
    _last_call: float = 0.0
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    # --- HTTP -----------------------------------------------------------------------
    def _authorize(self) -> str:
        if self._token and time.time() < self._token_until - 60:
            return self._token
        basic = base64.b64encode(f"{self.client_id}:{self.client_secret}".encode()).decode()
        request = urllib.request.Request(
            TOKEN_URL,
            data=urllib.parse.urlencode({"grant_type": "client_credentials"}).encode(),
            headers={"Authorization": f"Basic {basic}", "User-Agent": self.user_agent},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:  # noqa: S310 - fixed https URL
            payload = json.loads(response.read().decode("utf-8"))
        token = payload.get("access_token")
        if not token:
            raise OSError(f"no access token ({payload.get('error') or 'unknown'})")
        self._token = token
        self._token_until = time.time() + float(payload.get("expires_in") or 3600)
        return token

    def _get(self, path: str, params: dict) -> object:
        with self._lock:
            if self.calls >= MAX_CALLS:
                raise OSError(f"call cap {MAX_CALLS} reached")
            wait = CALL_SPACING - (time.monotonic() - self._last_call)
            if wait > 0:
                time.sleep(wait)
            self.calls += 1
            token = self._authorize()
            query = urllib.parse.urlencode({**params, "raw_json": 1})
            request = urllib.request.Request(
                f"{API_ROOT}{path}?{query}",
                headers={"Authorization": f"Bearer {token}", "User-Agent": self.user_agent},
            )
            try:
                with urllib.request.urlopen(request, timeout=TIMEOUT) as response:  # noqa: S310 - fixed host
                    return json.loads(response.read().decode("utf-8"))
            finally:
                self._last_call = time.monotonic()

    def _record(self, what: str, exc: Exception) -> None:
        code = getattr(exc, "code", None)
        self.errors.append(f"{what}: {f'HTTP {code}' if code else type(exc).__name__}")

    # --- API ------------------------------------------------------------------------
    def search(self, query: str, limit: int = 8) -> list[dict]:
        """Threads matching ``query`` as search-result rows (title, url, snippet, published)."""
        try:
            payload = self._get("/search", {"q": query, "limit": limit, "sort": "relevance", "t": "all", "type": "link"})
        except Exception as exc:  # noqa: BLE001 - recorded; the run goes on without Reddit
            self._record(f"search `{query}`", exc)
            return []
        rows: list[dict] = []
        for child in (payload or {}).get("data", {}).get("children", []):
            post = child.get("data") or {}
            if post.get("over_18") or not post.get("permalink"):
                continue
            rows.append(
                {
                    "title": _one_line(post.get("title")),
                    "url": WEB_ROOT + post["permalink"],
                    "snippet": _one_line(post.get("selftext"))[:300] or f"r/{post.get('subreddit', '')}",
                    "published": _day(post.get("created_utc")),
                    "via": "reddit_api",
                }
            )
        return rows

    def thread(self, url: str) -> dict:
        """Post and top comments of a thread: ``{"text", "published", "comments"}``. Empty dict on failure.

        ``text`` has one block per line (title, post paragraphs, one line per comment) so the
        evidence pack's excerpt step can pick the on-topic passages.
        """
        pid = post_id(url)
        if not pid:
            return {}
        try:
            payload = self._get(f"/comments/{pid}", {"limit": COMMENTS_PER_THREAD, "depth": 2, "sort": "top"})
        except Exception as exc:  # noqa: BLE001
            self._record(f"thread {pid}", exc)
            return {}
        if not isinstance(payload, list) or not payload:
            return {}
        posts = payload[0].get("data", {}).get("children", [])
        post = (posts[0].get("data") if posts else None) or {}
        lines = [_one_line(post.get("title"))]
        lines += [_one_line(p) for p in str(post.get("selftext") or "").split("\n") if _one_line(p)]
        comments = 0

        def walk(children: list) -> None:
            nonlocal comments
            for child in children:
                if child.get("kind") != "t1":
                    continue
                data = child.get("data") or {}
                body = _one_line(data.get("body"))
                if (
                    data.get("author") not in _SKIP_AUTHORS
                    and body not in _SKIP_BODIES
                    and len(body) >= MIN_COMMENT_CHARS
                ):
                    lines.append(body)
                    comments += 1
                replies = data.get("replies")
                if isinstance(replies, dict):
                    walk(replies.get("data", {}).get("children", []))

        if len(payload) > 1:
            walk(payload[1].get("data", {}).get("children", []))
        return {"text": "\n".join(line for line in lines if line), "published": _day(post.get("created_utc")), "comments": comments}


def reddit_from_env(environ: dict | None = None) -> RedditClient | None:
    """A client when credentials are configured (env vars or the ``CQR_REDDIT_CREDENTIALS`` file), else None."""
    env = os.environ if environ is None else environ
    client_id = env.get("REDDIT_CLIENT_ID", "")
    secret = env.get("REDDIT_CLIENT_SECRET", "")
    agent = env.get("REDDIT_USER_AGENT", "")
    path = env.get("CQR_REDDIT_CREDENTIALS", "")
    if (not client_id or not secret) and path:
        try:
            data = json.loads(Path(path).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            data = {}
        client_id = client_id or str(data.get("client_id") or "")
        secret = secret or str(data.get("client_secret") or "")
        agent = agent or str(data.get("user_agent") or "")
    if not client_id or not secret:
        return None
    return RedditClient(client_id, secret, agent or DEFAULT_USER_AGENT)
