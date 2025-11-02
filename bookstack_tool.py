"""
title: BookStack Tool
author: labels-en-meer
description: Search BookStack and automatically retrieve full page content. The AI gets direct access to complete documentation.
version: 1.2.0
requirements: requests
"""

import os
import html
import re
import requests
from typing import Any, Dict, Callable, Optional
from datetime import datetime
from pydantic import BaseModel, Field


# ---- Client with Session + retries ----
class BookStackClientRequestFailedError(ConnectionError):
    def __init__(self, status: int, error: str) -> None:
        self.status_code = status
        self.error = error
        super().__init__(
            f"BookStack Client request failed with status {status}: {error}"
        )


class BookStackApiClient:
    def __init__(
        self, base_url: str, token_id: str, token_secret: str, timeout: int = 30
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.token_id = token_id
        self.token_secret = token_secret
        self.timeout = timeout
        self.session = requests.Session()
        try:
            from requests.adapters import HTTPAdapter
            from urllib3.util.retry import Retry

            retry = Retry(
                total=3, backoff_factor=0.5, status_forcelist=[429, 500, 502, 503, 504]
            )
            self.session.mount("http://", HTTPAdapter(max_retries=retry))
            self.session.mount("https://", HTTPAdapter(max_retries=retry))
        except Exception:
            pass

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Token {self.token_id}:{self.token_secret}",
            "Accept": "application/json",
            "User-Agent": "OpenWebUI-BookStack-Tool/1.2.0",
        }

    def _api(self, endpoint: str) -> str:
        return f"{self.base_url}/api/{endpoint.lstrip('/')}"

    def app_url(self, endpoint: str) -> str:
        return f"{self.base_url}/{endpoint.lstrip('/')}"

    def get(
        self, endpoint: str, params: Dict[str, str] | None = None
    ) -> Dict[str, Any]:
        r = self.session.get(
            self._api(endpoint),
            headers=self._headers(),
            params=params or {},
            timeout=self.timeout,
        )
        try:
            data = r.json()
        except Exception:
            data = {}
        if r.status_code >= 300:
            msg = data.get("error", {}).get("message") or r.reason
            raise BookStackClientRequestFailedError(r.status_code, msg)
        return data

    def export_markdown(self, page_id: str) -> str:
        r = self.session.get(
            self._api(f"/pages/{page_id}/export-markdown"),
            headers=self._headers(),
            timeout=self.timeout,
        )
        if r.status_code >= 300:
            raise BookStackClientRequestFailedError(r.status_code, r.reason)
        return r.text


# ---- Tool Class ----
class Tools:
    class Valves(BaseModel):
        """Configuration for BookStack API access"""
        BOOKSTACK_URL: str = Field(
            default="",
            description="BookStack base URL (without trailing slash)",
        )
        BOOKSTACK_TOKEN_ID: str = Field(
            default="",
            description="BookStack API Token ID",
        )
        BOOKSTACK_TOKEN_SECRET: str = Field(
            default="",
            description="BookStack API Token Secret",
        )

    def __init__(self):
        # Initialize valves with configuration
        self.valves = self.Valves()
        # Disable automatic citations - we handle them manually
        self.citation = False

    def _client(self) -> BookStackApiClient:
        """Create a BookStack client with the valves configuration"""
        # Validate that configuration is set
        if not self.valves.BOOKSTACK_URL:
            raise ValueError(
                "BOOKSTACK_URL is not configured. "
                "Go to Settings → Tools → BookStack Tool and fill in the Valves."
            )
        if not self.valves.BOOKSTACK_TOKEN_ID or not self.valves.BOOKSTACK_TOKEN_SECRET:
            raise ValueError(
                "BookStack API credentials are not configured. "
                "Go to Settings → Tools → BookStack Tool and fill in BOOKSTACK_TOKEN_ID and BOOKSTACK_TOKEN_SECRET."
            )

        return BookStackApiClient(
            self.valves.BOOKSTACK_URL,
            self.valves.BOOKSTACK_TOKEN_ID,
            self.valves.BOOKSTACK_TOKEN_SECRET
        )

    def _optimize_query(self, query: str) -> str:
        """Optimize the search query for BookStack by removing stopwords"""
        # Dutch and English stopwords that add little value to the search
        stopwords = {
            'welke', 'wat', 'is', 'zijn', 'er', 'de', 'het', 'een', 'van', 'in',
            'voor', 'op', 'aan', 'met', 'te', 'hoe', 'kan', 'moet', 'waar',
            'which', 'what', 'is', 'are', 'the', 'a', 'an', 'of', 'in', 'for',
            'on', 'at', 'to', 'how', 'can', 'should', 'where', 'there'
        }

        # Split query into words and filter stopwords
        words = query.lower().split()
        important_words = [w for w in words if w not in stopwords and len(w) > 2]

        # If too few words remain, use original query
        if len(important_words) < 1:
            return query

        return " ".join(important_words)

    async def search(
        self,
        query: str,
        max_pages: int = 4,
        __event_emitter__: Optional[Callable[[dict], None]] = None,
    ) -> str:
        """
        Search BookStack and automatically retrieve full content of the most relevant pages.
        The AI gets direct access to the full content to answer questions.

        Args:
            query: Search term
            max_pages: Maximum number of pages to fully retrieve (default: 4)
        """
        # Optimize the query for better results
        optimized_query = self._optimize_query(query)

        if __event_emitter__:
            search_msg = f"Searching for: {optimized_query}" if optimized_query != query else "Searching BookStack..."
            await __event_emitter__(
                {
                    "type": "status",
                    "data": {"description": search_msg, "done": False},
                }
            )

        # Step 1: Search for relevant pages
        c = self._client()
        res = c.get("/search", {"query": optimized_query}).get("data", [])[:10]

        if not res:
            if __event_emitter__:
                await __event_emitter__(
                    {
                        "type": "status",
                        "data": {"description": "No results found", "done": True},
                    }
                )

            no_results_msg = f"**No results found** for '{query}'"
            if optimized_query != query:
                no_results_msg += f"\n\n_Searched for: '{optimized_query}'_"
                no_results_msg += f"\n\n💡 **Tip:** Try a different search term or use specific keywords from the documentation."

            return no_results_msg

        # Step 2: Filter only pages (books/chapters contain no direct content)
        pages = [r for r in res if r.get("type") == "page"][:max_pages]

        if not pages:
            # No pages found, show only search results
            output_lines = ["**No pages found, but these results were found:**\n"]
            for i, r in enumerate(res, 1):
                title = r.get("name", "No title")
                url = r.get("url", "")
                item_type = r.get("type", "unknown")
                item_id = r.get("id", "")
                output_lines.append(f"{i}. **{title}** ({item_type}, ID: {item_id})")
                output_lines.append(f"   🔗 [Open in BookStack]({url})\n")

            if __event_emitter__:
                await __event_emitter__(
                    {
                        "type": "status",
                        "data": {"description": "Only books/chapters found", "done": True},
                    }
                )

            return "\n".join(output_lines)

        # Step 3: Retrieve full content from found pages
        if __event_emitter__:
            page_titles = ", ".join([p.get("name", "?")[:30] for p in pages[:2]])
            if len(pages) > 2:
                page_titles += "..."
            await __event_emitter__(
                {
                    "type": "status",
                    "data": {
                        "description": f"Found: {page_titles}",
                        "done": False,
                    },
                }
            )

        # Show which query was used if it was optimized
        query_info = f"'{query}'"
        if optimized_query != query:
            query_info = f"'{query}' (searched for: '{optimized_query}')"

        output_lines = [f"**Found {len(pages)} relevant page(s) for {query_info}:**\n"]

        # Track if we successfully retrieved at least 1 page
        success_count = 0
        permission_error = False

        for idx, page in enumerate(pages, 1):
            page_id = page.get("id")
            title = page.get("name", "No title")
            url = page.get("url", "")
            excerpt = html.unescape(page.get("excerpt") or "")
            excerpt = re.sub(r"\s+", " ", excerpt).strip()

            try:
                # Status: Show which page we're retrieving
                if __event_emitter__:
                    await __event_emitter__(
                        {
                            "type": "status",
                            "data": {
                                "description": f"Retrieving: {title}...",
                                "done": False
                            },
                        }
                    )

                # Retrieve page metadata via the correct endpoint
                meta = c.get(f"/pages/{page_id}", {})

                # Try to get markdown content (if available)
                content = meta.get("markdown", "")

                # If no markdown, use the HTML content
                if not content:
                    content = meta.get("html", "")
                    if content:
                        # Convert HTML to readable text (basic)
                        content = html.unescape(content)
                        # Strip HTML tags but preserve line breaks
                        content = re.sub(r'<br\s*/?>', '\n', content)
                        content = re.sub(r'<p>', '\n', content)
                        content = re.sub(r'<[^>]+>', '', content)
                        content = re.sub(r'\n\s*\n+', '\n\n', content).strip()

                # Use URL from metadata if available
                full_url = meta.get("url") or url

                # Check if we have content
                if not content:
                    raise ValueError("No content available")

                # Add to output
                output_lines.append(f"\n---\n## Page {idx}: {title} (ID: {page_id})\n")
                output_lines.append(f"🔗 [Open in BookStack]({full_url})\n")
                output_lines.append(f"\n{content}\n")

                # Emit citation with full content
                if __event_emitter__:
                    await __event_emitter__(
                        {
                            "type": "citation",
                            "data": {
                                "document": [content],  # Full content for AI
                                "metadata": [
                                    {
                                        "date_accessed": datetime.now().isoformat(),
                                        "source": title,
                                        "url": full_url,
                                        "type": "bookstack_page",
                                        "page_id": page_id,
                                    }
                                ],
                                "source": {"name": title, "url": full_url},
                            },
                        }
                    )

                success_count += 1

            except BookStackClientRequestFailedError as e:
                # Specific BookStack API errors
                error_details = f"Page ID: {page_id}, Status: {e.status_code}, Error: {e.error}"

                if e.status_code == 403:
                    permission_error = True
                    # Fallback to excerpt if we don't have permission
                    output_lines.append(f"\n---\n## Page {idx}: {title} (ID: {page_id})\n")
                    output_lines.append(f"🔗 [Open in BookStack]({url})\n")
                    output_lines.append(f"\n⚠️ **No access to full page** (403 Forbidden)\n")
                    output_lines.append(f"Debug: {error_details}\n")
                    if excerpt:
                        output_lines.append(f"\n**Summary:** {excerpt}\n")

                    # Emit citation with excerpt
                    if __event_emitter__:
                        await __event_emitter__(
                            {
                                "type": "citation",
                                "data": {
                                    "document": [excerpt or title],
                                    "metadata": [
                                        {
                                            "date_accessed": datetime.now().isoformat(),
                                            "source": title,
                                            "url": url,
                                            "type": "bookstack_page_excerpt",
                                            "page_id": page_id,
                                            "note": "Full content not available (API permission)",
                                        }
                                    ],
                                    "source": {"name": title, "url": url},
                                },
                            }
                        )
                elif e.status_code == 404:
                    output_lines.append(f"\n---\n## Page {idx}: {title} (ID: {page_id})\n")
                    output_lines.append(f"🔗 [Open in BookStack]({url})\n")
                    output_lines.append(f"\n⚠️ **Page not found** (404 Not Found)\n")
                    output_lines.append(f"Debug: {error_details}\n")
                    output_lines.append(f"Possible issue: Page ID from search does not match API\n")
                    if excerpt:
                        output_lines.append(f"\n**Summary:** {excerpt}\n")
                else:
                    output_lines.append(f"\n---\n## Page {idx}: {title} (ID: {page_id})\n")
                    output_lines.append(f"🔗 [Open in BookStack]({url})\n")
                    output_lines.append(f"\n⚠️ **API Error**\n")
                    output_lines.append(f"Debug: {error_details}\n")
                    if excerpt:
                        output_lines.append(f"\n**Summary:** {excerpt}\n")

            except Exception as e:
                # Unexpected errors
                output_lines.append(f"\n---\n## Page {idx}: {title} (ID: {page_id})\n")
                output_lines.append(f"🔗 [Open in BookStack]({url})\n")
                output_lines.append(f"\n⚠️ **Unexpected error**: {type(e).__name__}\n")
                output_lines.append(f"Details: {str(e)}\n")
                if excerpt:
                    output_lines.append(f"\n**Summary:** {excerpt}\n")

        # Add warning if we had permission errors
        if permission_error:
            output_lines.append("\n\n---\n")
            output_lines.append("⚠️ **API Permission Issue Detected**\n\n")
            output_lines.append("The BookStack API token does not have permission to retrieve full pages.\n")
            output_lines.append("Only summaries (excerpts) are available.\n\n")
            output_lines.append("**Solution:**\n")
            output_lines.append("1. Go to your BookStack profile → API Tokens\n")
            output_lines.append("2. Check the token permissions\n")
            output_lines.append("3. Ensure the token has 'View' permissions for Pages\n")
            output_lines.append("4. Or ask the administrator for a token with more permissions\n")

        if __event_emitter__:
            if success_count > 0:
                status_msg = f"✓ {success_count} page(s) successfully retrieved"
            else:
                status_msg = "Search completed (only summaries available)"
            await __event_emitter__(
                {
                    "type": "status",
                    "data": {"description": status_msg, "done": True},
                }
            )

        return "\n".join(output_lines)

    async def get_page(
        self,
        page_id: int,
        format: str = "markdown",
        __event_emitter__: Optional[Callable[[dict], None]] = None,
    ) -> str:
        """
        Retrieve page content from BookStack with citation.

        Args:
            page_id: ID of the page
            format: Format of the content (markdown, text, or html)
        """
        # Status update
        if __event_emitter__:
            await __event_emitter__(
                {
                    "type": "status",
                    "data": {"description": "Retrieving page...", "done": False},
                }
            )

        c = self._client()
        meta = c.get(f"/pages/{page_id}", {})
        title = meta.get("name", "Unknown page")
        url = meta.get("url", "")

        # Retrieve content in desired format
        if format == "markdown":
            # Try markdown from metadata
            content = meta.get("markdown", "")
            if not content:
                # Fallback to HTML
                content = meta.get("html", "")
                if content:
                    content = html.unescape(content)
                    content = re.sub(r'<br\s*/?>', '\n', content)
                    content = re.sub(r'<p>', '\n', content)
                    content = re.sub(r'<[^>]+>', '', content)
                    content = re.sub(r'\n\s*\n+', '\n\n', content).strip()
        elif format == "text":
            # Text format: use HTML and strip all tags
            content = meta.get("html", "")
            if content:
                content = html.unescape(content)
                content = re.sub(r'<[^>]+>', ' ', content)
                content = re.sub(r'\s+', ' ', content).strip()
        elif format == "html":
            content = meta.get("html") or ""
        else:
            raise ValueError("format must be markdown|text|html")

        # Emit citation for this page
        if __event_emitter__:
            await __event_emitter__(
                {
                    "type": "citation",
                    "data": {
                        "document": [
                            content[:500] + "..." if len(content) > 500 else content
                        ],
                        "metadata": [
                            {
                                "date_accessed": datetime.now().isoformat(),
                                "source": title,
                                "url": url,
                                "type": "bookstack_page",
                                "page_id": page_id,
                            }
                        ],
                        "source": {"name": title, "url": url},
                    },
                }
            )

            # Update status
            await __event_emitter__(
                {
                    "type": "status",
                    "data": {"description": "Page loaded!", "done": True},
                }
            )

        # Format output with link
        output = f"# {title}\n\n"
        output += f"🔗 [Open in BookStack]({url})\n\n"
        output += "---\n\n"
        output += content

        return output
