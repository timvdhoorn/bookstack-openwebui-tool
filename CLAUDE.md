# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This repository contains a BookStack integration tool for Open WebUI. The tool enables AI assistants in Open WebUI to search BookStack documentation and retrieve full page content with automatic citations.

**Key Technology:**
- Python 3 with type hints (Pydantic BaseModel)
- BookStack REST API integration
- Open WebUI Tools framework with async support

## Core Architecture

### Main Component: `bookstack_tool.py`

The tool is implemented as a single Python file with three main classes:

1. **`BookStackApiClient`**: HTTP client wrapper with automatic retries
   - Handles authentication via Token ID/Secret
   - Implements retry logic for transient failures (429, 500, 502, 503, 504)
   - Provides typed methods: `get()` for JSON, `export_markdown()` for markdown content
   - Base URL normalization (strips trailing slashes)

2. **`Tools.Valves`**: Configuration class (nested within Tools)
   - Uses Pydantic `BaseModel` for type-safe configuration
   - Three required fields: `BOOKSTACK_URL`, `BOOKSTACK_TOKEN_ID`, `BOOKSTACK_TOKEN_SECRET`
   - Empty defaults force users to configure via Open WebUI interface
   - **Important**: Must be a nested class for Open WebUI GUI integration

3. **`Tools`**: Main tool class with async methods
   - `search(query, max_pages=2)`: Searches BookStack and auto-fetches full page content
   - `get_page(page_id, format="markdown")`: Retrieves single page by ID
   - `_optimize_query()`: Removes stopwords for better search results
   - All methods support `__event_emitter__` for status updates and citations

### Key Design Patterns

**Citations System:**
- Manual citation management (`self.citation = False` disables automatic citations)
- Emits citation events with full content via `__event_emitter__`
- Citations include metadata: `date_accessed`, `source`, `url`, `type`, `page_id`

**Error Handling:**
- Custom exception: `BookStackClientRequestFailedError` with status code
- Graceful degradation: Falls back to excerpts when full page access is denied (403)
- Detailed error messages guide users to check permissions/configuration

**Query Optimization:**
- Removes Dutch and English stopwords before search
- Preserves original query if too few keywords remain
- Improves search relevance without user intervention

## Development Commands

### Testing

```bash
# Test BookStack API connectivity
python3 test_bookstack_api.py

# Verify Valves structure (Open WebUI compatibility)
python3 test_valves_structure.py
```

### Installation in Open WebUI

1. Upload `bookstack_tool.py` via Settings → Tools
2. Configure Valves with BookStack credentials
3. Test with: "Zoek naar [query]" or "Haal pagina [id] op"

### Manual API Testing

```bash
# Test search endpoint
curl -H "Authorization: Token TOKEN_ID:TOKEN_SECRET" \
     -H "Accept: application/json" \
     "https://your-bookstack.com/api/search?query=test"

# Test page retrieval
curl -H "Authorization: Token TOKEN_ID:TOKEN_SECRET" \
     "https://your-bookstack.com/api/pages/42"
```

## Common Development Scenarios

### Modifying Search Behavior

The `search()` method has several stages:
1. Query optimization (`_optimize_query()`)
2. BookStack API search call (`/api/search`)
3. Filter to pages only (books/chapters have no direct content)
4. Parallel page content retrieval for up to `max_pages` pages
5. Citation emission for each successfully retrieved page

### Adding New Output Formats

The `get_page()` method supports three formats:
- `"markdown"`: Prefers `meta.get("markdown")`, falls back to HTML stripping
- `"text"`: Strips all HTML tags, collapses whitespace
- `"html"`: Returns raw HTML from `meta.get("html")`

To add a format, modify the format handling block in `get_page()` at line 437.

### Handling API Permissions

The tool implements automatic fallback for 403 (Forbidden) errors:
- Displays excerpts when full content is unavailable
- Emits citations with type `"bookstack_page_excerpt"`
- Provides detailed error messages referencing permissions

Minimum required BookStack permissions:
- View all books
- View all chapters
- View all pages

## Configuration Notes

**Valves Structure Requirements:**
- Must be nested class inside `Tools` (not module-level)
- Must inherit from `pydantic.BaseModel`
- Field descriptions appear in Open WebUI GUI
- Empty defaults (`""`) force explicit configuration

**API Client:**
- Default timeout: 30 seconds (configurable in `BookStackApiClient.__init__`)
- Automatic HTTPS upgrade for HTTP URLs
- Session-based connections with retry adapter (uses `requests.Session`)

## Important Gotchas

1. **Valves Placement**: The `Valves` class must be nested inside `Tools`, not at module level. Open WebUI's introspection requires this specific structure.

2. **Citation Format**: The `document` field in citations must be a list, even for single strings: `"document": [content]`

3. **URL Construction**: Always strip trailing slashes from base URLs before API calls to avoid double-slash issues

4. **Page Type Filtering**: BookStack's search returns books/chapters/shelves, but only pages have markdown content. Always filter to `type == "page"` when fetching full content.

5. **Async Requirements**: All tool methods must be `async` even if not using `await` internally, to support `__event_emitter__` callbacks.

## Documentation Files

- **`README.md`**: User-facing documentation (Dutch) with installation and usage instructions
- **`CHANGELOG.md`**: Version history and migration notes
