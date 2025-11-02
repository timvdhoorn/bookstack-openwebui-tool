"""
title: BookStack Tool
author: labels-en-meer
description: Zoekt in BookStack en haalt automatisch volledige pagina-inhoud op. De AI krijgt direct toegang tot complete documentatie.
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


# ---- Client met Session + retries ----
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
            description="BookStack base URL (zonder trailing slash)",
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
        """Maak een BookStack client met de valves configuratie"""
        # Valideer of de configuratie is ingesteld
        if not self.valves.BOOKSTACK_URL:
            raise ValueError(
                "BOOKSTACK_URL is niet ingesteld. "
                "Ga naar Settings → Tools → BookStack Tool en vul de Valves in."
            )
        if not self.valves.BOOKSTACK_TOKEN_ID or not self.valves.BOOKSTACK_TOKEN_SECRET:
            raise ValueError(
                "BookStack API credentials zijn niet ingesteld. "
                "Ga naar Settings → Tools → BookStack Tool en vul BOOKSTACK_TOKEN_ID en BOOKSTACK_TOKEN_SECRET in."
            )

        return BookStackApiClient(
            self.valves.BOOKSTACK_URL,
            self.valves.BOOKSTACK_TOKEN_ID,
            self.valves.BOOKSTACK_TOKEN_SECRET
        )

    def _optimize_query(self, query: str) -> str:
        """Optimaliseer de zoekquery voor BookStack door stopwoorden te verwijderen"""
        # Nederlandse en Engelse stopwoorden die weinig toevoegen aan de search
        stopwoorden = {
            'welke', 'wat', 'is', 'zijn', 'er', 'de', 'het', 'een', 'van', 'in',
            'voor', 'op', 'aan', 'met', 'te', 'hoe', 'kan', 'moet', 'waar',
            'which', 'what', 'is', 'are', 'the', 'a', 'an', 'of', 'in', 'for',
            'on', 'at', 'to', 'how', 'can', 'should', 'where', 'there'
        }

        # Split query in woorden en filter stopwoorden
        woorden = query.lower().split()
        belangrijke_woorden = [w for w in woorden if w not in stopwoorden and len(w) > 2]

        # Als we te weinig woorden overhouden, gebruik originele query
        if len(belangrijke_woorden) < 1:
            return query

        return " ".join(belangrijke_woorden)

    async def search(
        self,
        query: str,
        max_pages: int = 4,
        __event_emitter__: Optional[Callable[[dict], None]] = None,
    ) -> str:
        """
        Zoek in BookStack en haal automatisch de volledige inhoud op van de meest relevante pagina's.
        De AI krijgt direct toegang tot de volledige content om vragen mee te beantwoorden.

        Args:
            query: Zoekterm
            max_pages: Maximum aantal pagina's om volledig op te halen (standaard: 4)
        """
        # Optimaliseer de query voor betere resultaten
        optimized_query = self._optimize_query(query)

        if __event_emitter__:
            search_msg = f"Zoeken naar: {optimized_query}" if optimized_query != query else "Zoeken in BookStack..."
            await __event_emitter__(
                {
                    "type": "status",
                    "data": {"description": search_msg, "done": False},
                }
            )

        # Stap 1: Zoek naar relevante pagina's
        c = self._client()
        res = c.get("/search", {"query": optimized_query}).get("data", [])[:5]

        if not res:
            if __event_emitter__:
                await __event_emitter__(
                    {
                        "type": "status",
                        "data": {"description": "Geen resultaten gevonden", "done": True},
                    }
                )

            no_results_msg = f"**Geen resultaten gevonden** voor '{query}'"
            if optimized_query != query:
                no_results_msg += f"\n\n_Gezocht op: '{optimized_query}'_"
                no_results_msg += f"\n\n💡 **Tip:** Probeer een andere zoekterm of gebruik specifieke trefwoorden uit de documentatie."

            return no_results_msg

        # Stap 2: Filter alleen pages (books/chapters bevatten geen directe content)
        pages = [r for r in res if r.get("type") == "page"][:max_pages]

        if not pages:
            # Geen pages gevonden, toon alleen zoekresultaten
            output_lines = ["**Geen pagina's gevonden, maar wel deze resultaten:**\n"]
            for i, r in enumerate(res, 1):
                title = r.get("name", "Geen titel")
                url = r.get("url", "")
                item_type = r.get("type", "unknown")
                item_id = r.get("id", "")
                output_lines.append(f"{i}. **{title}** ({item_type}, ID: {item_id})")
                output_lines.append(f"   🔗 [Open in BookStack]({url})\n")

            if __event_emitter__:
                await __event_emitter__(
                    {
                        "type": "status",
                        "data": {"description": "Alleen books/chapters gevonden", "done": True},
                    }
                )

            return "\n".join(output_lines)

        # Stap 3: Haal volledige content op van de gevonden pages
        if __event_emitter__:
            page_titles = ", ".join([p.get("name", "?")[:30] for p in pages[:2]])
            if len(pages) > 2:
                page_titles += "..."
            await __event_emitter__(
                {
                    "type": "status",
                    "data": {
                        "description": f"Gevonden: {page_titles}",
                        "done": False,
                    },
                }
            )

        # Toon welke query gebruikt werd als deze geoptimaliseerd is
        query_info = f"'{query}'"
        if optimized_query != query:
            query_info = f"'{query}' (gezocht op: '{optimized_query}')"

        output_lines = [f"**Gevonden {len(pages)} relevante pagina(s) voor {query_info}:**\n"]

        # Track of we tenminste 1 pagina succesvol ophaalden
        success_count = 0
        permission_error = False

        for idx, page in enumerate(pages, 1):
            page_id = page.get("id")
            title = page.get("name", "Geen titel")
            url = page.get("url", "")
            excerpt = html.unescape(page.get("excerpt") or "")
            excerpt = re.sub(r"\s+", " ", excerpt).strip()

            try:
                # Status: Toon welke pagina we ophalen
                if __event_emitter__:
                    await __event_emitter__(
                        {
                            "type": "status",
                            "data": {
                                "description": f"Ophalen: {title}...",
                                "done": False
                            },
                        }
                    )

                # Haal pagina metadata op via het correcte endpoint
                meta = c.get(f"/pages/{page_id}", {})

                # Probeer markdown content te krijgen (als beschikbaar)
                content = meta.get("markdown", "")

                # Als geen markdown, gebruik de HTML content
                if not content:
                    content = meta.get("html", "")
                    if content:
                        # Converteer HTML naar leesbare tekst (basis)
                        content = html.unescape(content)
                        # Strip HTML tags maar behoud line breaks
                        content = re.sub(r'<br\s*/?>', '\n', content)
                        content = re.sub(r'<p>', '\n', content)
                        content = re.sub(r'<[^>]+>', '', content)
                        content = re.sub(r'\n\s*\n+', '\n\n', content).strip()

                # Gebruik URL uit metadata als die beschikbaar is
                full_url = meta.get("url") or url

                # Check of we content hebben
                if not content:
                    raise ValueError("Geen content beschikbaar")

                # Voeg toe aan output
                output_lines.append(f"\n---\n## Pagina {idx}: {title} (ID: {page_id})\n")
                output_lines.append(f"🔗 [Open in BookStack]({full_url})\n")
                output_lines.append(f"\n{content}\n")

                # Emit citation met volledige content
                if __event_emitter__:
                    await __event_emitter__(
                        {
                            "type": "citation",
                            "data": {
                                "document": [content],  # Volledige content voor AI
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
                # Specifieke BookStack API errors
                error_details = f"Page ID: {page_id}, Status: {e.status_code}, Error: {e.error}"

                if e.status_code == 403:
                    permission_error = True
                    # Fallback naar excerpt als we geen permissie hebben
                    output_lines.append(f"\n---\n## Pagina {idx}: {title} (ID: {page_id})\n")
                    output_lines.append(f"🔗 [Open in BookStack]({url})\n")
                    output_lines.append(f"\n⚠️ **Geen toegang tot volledige pagina** (403 Forbidden)\n")
                    output_lines.append(f"Debug: {error_details}\n")
                    if excerpt:
                        output_lines.append(f"\n**Samenvatting:** {excerpt}\n")

                    # Emit citation met excerpt
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
                                            "note": "Volledige content niet beschikbaar (API permissie)",
                                        }
                                    ],
                                    "source": {"name": title, "url": url},
                                },
                            }
                        )
                elif e.status_code == 404:
                    output_lines.append(f"\n---\n## Pagina {idx}: {title} (ID: {page_id})\n")
                    output_lines.append(f"🔗 [Open in BookStack]({url})\n")
                    output_lines.append(f"\n⚠️ **Pagina niet gevonden** (404 Not Found)\n")
                    output_lines.append(f"Debug: {error_details}\n")
                    output_lines.append(f"Mogelijk probleem: Page ID uit search komt niet overeen met API\n")
                    if excerpt:
                        output_lines.append(f"\n**Samenvatting:** {excerpt}\n")
                else:
                    output_lines.append(f"\n---\n## Pagina {idx}: {title} (ID: {page_id})\n")
                    output_lines.append(f"🔗 [Open in BookStack]({url})\n")
                    output_lines.append(f"\n⚠️ **API Error**\n")
                    output_lines.append(f"Debug: {error_details}\n")
                    if excerpt:
                        output_lines.append(f"\n**Samenvatting:** {excerpt}\n")

            except Exception as e:
                # Onverwachte errors
                output_lines.append(f"\n---\n## Pagina {idx}: {title} (ID: {page_id})\n")
                output_lines.append(f"🔗 [Open in BookStack]({url})\n")
                output_lines.append(f"\n⚠️ **Onverwachte fout**: {type(e).__name__}\n")
                output_lines.append(f"Details: {str(e)}\n")
                if excerpt:
                    output_lines.append(f"\n**Samenvatting:** {excerpt}\n")

        # Voeg waarschuwing toe als we permission errors hadden
        if permission_error:
            output_lines.append("\n\n---\n")
            output_lines.append("⚠️ **API Permissie Probleem Gedetecteerd**\n\n")
            output_lines.append("De BookStack API token heeft geen permissie om volledige pagina's op te halen.\n")
            output_lines.append("Er zijn alleen samenvattingen (excerpts) beschikbaar.\n\n")
            output_lines.append("**Oplossing:**\n")
            output_lines.append("1. Ga naar je BookStack profiel → API Tokens\n")
            output_lines.append("2. Controleer de permissies van de token\n")
            output_lines.append("3. Zorg dat de token 'View' permissies heeft voor Pages\n")
            output_lines.append("4. Of vraag de beheerder om een token met meer permissies\n")

        if __event_emitter__:
            if success_count > 0:
                status_msg = f"✓ {success_count} pagina('s) succesvol opgehaald"
            else:
                status_msg = "Zoeken voltooid (alleen samenvattingen beschikbaar)"
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
        Haal pagina-inhoud op uit BookStack met bronvermelding.

        Args:
            page_id: ID van de pagina
            format: Formaat van de inhoud (markdown, text, of html)
        """
        # Status update
        if __event_emitter__:
            await __event_emitter__(
                {
                    "type": "status",
                    "data": {"description": "Pagina ophalen...", "done": False},
                }
            )

        c = self._client()
        meta = c.get(f"/pages/{page_id}", {})
        title = meta.get("name", "Onbekende pagina")
        url = meta.get("url", "")

        # Haal content op in gewenst formaat
        if format == "markdown":
            # Probeer markdown uit de metadata
            content = meta.get("markdown", "")
            if not content:
                # Fallback naar HTML
                content = meta.get("html", "")
                if content:
                    content = html.unescape(content)
                    content = re.sub(r'<br\s*/?>', '\n', content)
                    content = re.sub(r'<p>', '\n', content)
                    content = re.sub(r'<[^>]+>', '', content)
                    content = re.sub(r'\n\s*\n+', '\n\n', content).strip()
        elif format == "text":
            # Text format: gebruik HTML en strip alle tags
            content = meta.get("html", "")
            if content:
                content = html.unescape(content)
                content = re.sub(r'<[^>]+>', ' ', content)
                content = re.sub(r'\s+', ' ', content).strip()
        elif format == "html":
            content = meta.get("html") or ""
        else:
            raise ValueError("format must be markdown|text|html")

        # Emit citation voor deze pagina
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
                    "data": {"description": "Pagina geladen!", "done": True},
                }
            )

        # Formatteer output met link
        output = f"# {title}\n\n"
        output += f"🔗 [Open in BookStack]({url})\n\n"
        output += "---\n\n"
        output += content

        return output
