# Changelog - BookStack Tool

## Version 1.2.1 - 2025-11-02

### 🔧 Fixed
- **Clickable citations**: Citations now appear as clickable numbered references `[0]`, `[1]`, `[2]`, etc. in Open WebUI
- Added citation index markers to page titles in search results
- Fixed issue where citations appeared as `[00]` placeholders instead of interactive links

### ✨ Improvements
- Citations are now properly numbered and displayed in the response text
- Both `search()` and `get_page()` methods include citation markers
- Improved citation visibility in the Open WebUI interface

## Version 1.2.0 - 2025-11-02

### ✨ Improvements
- **Default max_pages increased**: Changed from 2 to 4 pages for more comprehensive search results
- **English translation**: All code, documentation, and messages translated to English for international audience

### 🌍 Translation
- Translated all docstrings and comments to English
- Translated error messages and status updates
- Translated README.md and CHANGELOG.md
- Updated CLAUDE.md with English references

## Version 1.1.0 - 2025-10-30

### 🔧 Fixed
- **404 Error resolved**: Tool now uses Open WebUI's Valves system for configuration
- Environment variables are no longer used (didn't work in Open WebUI)

### ✨ Improvements
- **Valves Configuration**: Credentials can now be set via the Open WebUI interface
- **Fallback values**: Tool works out-of-the-box with default credentials
- **Better integration**: Seamless operation with Open WebUI's configuration system

### 🔨 Technical changes
- Added: `Valves` class with Pydantic for type-safe configuration
- Changed: `_client()` is now a method of the `Tools` class instead of a global function
- All tool methods now use `self._client()` for API access
- Removed: Unused `List` import
- Cleaned up: Debug logging removed

### 📋 How to use in Open WebUI

1. Upload the updated `bookstack_tool.py` to Open WebUI
2. Go to **Settings → Tools → BookStack Tool**
3. Adjust the Valves if needed:
   - `BOOKSTACK_URL`: https://docs.example.com
   - `BOOKSTACK_TOKEN_ID`: Your BookStack API Token ID
   - `BOOKSTACK_TOKEN_SECRET`: Your BookStack API Token Secret
4. Save and test the tool

### 🎯 Functions

The tool has two functions:

1. **`search(query, max_pages=4)`**
   - Search BookStack
   - Returns list of results
   - Includes citations

2. **`get_page(page_id, format="markdown")`**
   - Retrieve full page
   - Supports: markdown, text, html
   - Includes citation

### ✅ Tested and working

The API is tested and works correctly:
```bash
curl -H "Authorization: Token TOKEN_ID:TOKEN_SECRET" \
     "https://docs.example.com/api/search?query=test"
# HTTP 200 OK - 3 results
```

## Version 1.0.0 - 2025-04-03

### ✨ New
- Basic implementation with search, get_page functions
- Environment variables for configuration
- Citations support
- Status updates via event emitters
