# BookStack Tool for Open WebUI

**Version:** 1.2.0
**Author:** timvdhoorn

## 📖 Description

A simple and reliable tool for searching BookStack and retrieving page content within Open WebUI. The tool integrates seamlessly with BookStack's API and provides automatic citations.

## ✨ Features

### 1. `search(query, max_pages=4)`
Search BookStack documentation.

**Parameters:**
- `query` (str): Search term
- `max_pages` (int, optional): Maximum number of results to fully retrieve (default: 4)

**Example:**
```
Search for "bartender license"
```

**Output:**
- List of search results
- For each result: title, type (page/book/chapter/shelf), excerpt, and link
- Automatic citations in Open WebUI

### 2. `get_page(page_id, format="markdown")`
Retrieve a complete page from BookStack.

**Parameters:**
- `page_id` (int): ID of the page
- `format` (str, optional): Format of the content
  - `"markdown"` (default) - Markdown format
  - `"text"` - Plain text
  - `"html"` - HTML format

**Example:**
```
Retrieve page 42 in markdown format
```

**Output:**
- Full page content
- Title and link to BookStack
- Automatic citation

## 🔧 Installation & Configuration

### 1. Upload the Tool
1. Download `bookstack_tool.py`
2. Open Open WebUI
3. Go to **Settings → Tools**
4. Click **Upload** and select `bookstack_tool.py`

### 2. Configure Valves
1. Go to **Settings → Tools → BookStack Tool**
2. Click on the **gear icon** (Valves)
3. Fill in the following fields:

   | Field | Description | Example |
   |-------|-------------|---------|
   | **BOOKSTACK_URL** | BookStack base URL (without trailing slash) | `https://docs.example.com` |
   | **BOOKSTACK_TOKEN_ID** | BookStack API Token ID | `5GGYx39SNweDUczbY7nFVoptIXZ37QIK` |
   | **BOOKSTACK_TOKEN_SECRET** | BookStack API Token Secret | `2xjo15QF6KV67gduvrjdpqOcscijel5C` |

4. Click **Save**

### 3. Creating a BookStack API Token

If you don't have an API token yet:

1. Log in to your BookStack instance
2. Go to your **profile** (top right)
3. Click on **API Tokens**
4. Click **Create Token**
5. Give it a name (e.g., "Open WebUI")
6. Copy the **Token ID** and **Token Secret**
7. Fill these in the Valves configuration

## 📝 Usage Examples

### Example 1: Searching for Information
```
Use the search function to search for "label printer installation"
```

**Result:**
```
Search results in BookStack:

1. Label printer installation preparation (page)
   Checklist for preparing label printer installations...
   🔗 Open in BookStack

2. SATO printer configuration (page)
   Guide for configuring SATO printers...
   🔗 Open in BookStack
```

### Example 2: Retrieving Full Page
```
Retrieve page 57 about label software installation
```

**Result:**
```
# Label software installation preparation

🔗 Open in BookStack

---

[Full markdown content of the page]
```

### Example 3: Workflow for Quick Answers
```
1. First search with search() for relevant pages
2. Note the page ID from the results
3. Use get_page(page_id) to retrieve the full content
```

## 🔍 Search Syntax

BookStack supports advanced search syntax:

| Syntax | Description | Example |
|--------|-------------|---------|
| `word1 word2` | Both words must appear | `printer installation` |
| `"exact phrase"` | Exact match | `"bartender license"` |
| `{created_by:me}` | Only created by you | `backup {created_by:me}` |
| `{type:page}` | Only pages | `installation {type:page}` |
| `{type:book}` | Only books | `manual {type:book}` |

## ⚠️ Error Messages

### "BOOKSTACK_URL is not configured"
**Solution:** Fill in the Valves via Settings → Tools → BookStack Tool

### "BookStack API credentials are not configured"
**Solution:** Fill in BOOKSTACK_TOKEN_ID and BOOKSTACK_TOKEN_SECRET in the Valves

### "BookStack Client request failed with status 404"
**Possible causes:**
- BOOKSTACK_URL is incorrect (check for trailing slash)
- Page does not exist
- API endpoint does not exist on this BookStack version

**Solution:**
1. Check if the URL is correct: `https://docs.example.com` (without `/` at the end)
2. Test the API manually:
   ```bash
   curl -H "Authorization: Token TOKEN_ID:TOKEN_SECRET" \
        "https://docs.example.com/api/search?query=test"
   ```

### "BookStack Client request failed with status 401"
**Solution:** Token ID or Secret is incorrect - check the credentials

### "BookStack Client request failed with status 403"
**Solution:** Your account does not have API access - contact the BookStack administrator

## 🛠️ Troubleshooting

### API Test
Test if the BookStack API is reachable:

```bash
# Replace TOKEN_ID and TOKEN_SECRET with your credentials
curl -H "Authorization: Token TOKEN_ID:TOKEN_SECRET" \
     -H "Accept: application/json" \
     "https://docs.example.com/api/search?query=test"
```

**Expected result:** HTTP 200 with JSON response

### Check Logs
Check the Open WebUI logs for more details:

```bash
docker logs <open-webui-container-name> 2>&1 | tail -50
```

### Reload Tool
1. Go to Settings → Tools
2. Remove the BookStack Tool
3. Restart Open WebUI
4. Upload the tool again
5. Reconfigure the Valves

## 📊 Features

✅ **Automatic citations** - All results are automatically added as sources in Open WebUI
✅ **Retry mechanism** - Automatic retry on transient errors (429, 500, 502, 503, 504)
✅ **Timeout handling** - Configurable timeout (default 30s)
✅ **Status updates** - Real-time status updates while retrieving pages
✅ **Multiple formats** - Markdown, text, or HTML output
✅ **URL construction** - Automatic construction of readable BookStack URLs
✅ **Error handling** - Clear error messages on problems

## 🔒 Security

- ⚠️ **API credentials** are stored in Open WebUI's database
- 🔐 Credentials are only visible to users with tool management rights
- 🚫 Credentials are **not** logged in application logs
- ✅ Always use HTTPS for the BOOKSTACK_URL

## 📚 API Reference

This tool uses the BookStack REST API:
- Endpoint: `/api/search` - Search content
- Endpoint: `/api/pages/{id}` - Page metadata
- Endpoint: `/api/pages/{id}/export-markdown` - Markdown export
- Endpoint: `/api/pages/{id}/export-plain-text` - Plain text export

Documentation: https://demo.bookstackapp.com/api/docs

## 🔄 Changelog

### v1.2.0 (2025-11-02)
- ✅ **Changed:** Default max_pages from 2 to 4 for more comprehensive search results
- ✅ **Improved:** English translation for international audience

### v1.1.0 (2025-10-30)
- ❌ **Removed:** `quick_answer()` function (too complex and error-prone)
- ✅ **Improved:** Simplified workflow with only `search()` and `get_page()`
- ✅ **Added:** Validation for empty Valves with clear error messages
- ✅ **Changed:** Removed default values from Valves (user must fill in)

### v1.0.0 (2025-10-30)
- ✅ **Fixed:** Valves as nested class within Tools (GUI now works!)
- ✅ **Added:** Clear descriptions for Valves fields

### v0.3.0 (2025-04-03)
- 🎉 First release
- ✅ Basic functionality: search, get_page
- ✅ Citations support

## 📞 Support

For questions or problems:
1. Check the troubleshooting section above first
2. Check the Open WebUI logs
3. Test the BookStack API manually
4. Contact the tool maintainer

## 📄 License

GPLv3

## 🙏 Credits

- **Open WebUI** - Platform for LLM interfaces
- **BookStack** - Open-source documentation platform
- **timvdhoorn** - Tool author
