# BookStack Tool for Open WebUI

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![Python](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Open WebUI](https://img.shields.io/badge/Open%20WebUI-Compatible-green.svg)](https://github.com/open-webui/open-webui)

A powerful integration tool that connects [BookStack](https://www.bookstackapp.com/) documentation with [Open WebUI](https://github.com/open-webui/open-webui), enabling AI assistants to search and retrieve documentation with automatic citations.

## ✨ Features

- 🔍 **Smart Search** - Search BookStack with automatic query optimization
- 📄 **Full Page Retrieval** - Get complete page content in markdown, text, or HTML
- 📚 **Auto Citations** - Automatic source citations in Open WebUI
- 🔄 **Retry Logic** - Handles transient API errors gracefully
- ⚡ **Real-time Updates** - Status updates during content retrieval
- 🛡️ **Secure** - Token-based authentication with BookStack API

## 🚀 Quick Start

### 1. Install

1. Download `bookstack_tool.py`
2. In Open WebUI: **Settings → Tools → Upload**
3. Select `bookstack_tool.py`

### 2. Configure

1. Go to **Settings → Tools → BookStack Tool**
2. Click the **gear icon** (Valves)
3. Fill in your BookStack credentials:
   - `BOOKSTACK_URL`: Your BookStack URL (e.g., `https://docs.example.com`)
   - `BOOKSTACK_TOKEN_ID`: API Token ID from BookStack
   - `BOOKSTACK_TOKEN_SECRET`: API Token Secret

## 📖 Documentation

For detailed documentation, see [DOCUMENTATION.md](DOCUMENTATION.md)

## 🔧 API Methods

### `search(query, max_pages=4)`

Search BookStack and automatically retrieve full content of the most relevant pages.

**Parameters:**

- `query` (str): Search term
- `max_pages` (int): Maximum pages to retrieve (default: 4)

### `get_page(page_id, format="markdown")`

Retrieve a specific page by ID.

**Parameters:**

- `page_id` (int): BookStack page ID
- `format` (str): Output format - `"markdown"`, `"text"`, or `"html"`

## 🔑 BookStack API Token

To create an API token in BookStack:

1. Log in to BookStack
2. Click your profile (top right)
3. Go to **API Tokens**
4. Click **Create Token**
5. Copy the Token ID and Secret

## 📋 Requirements

- Python 3.8+
- Open WebUI
- BookStack instance with API access
- `requests` library (auto-installed)

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📄 License

This project is licensed under the GNU General Public License v3.0 - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [Open WebUI](https://github.com/open-webui/open-webui) - Amazing LLM interface
- [BookStack](https://www.bookstackapp.com/) - Excellent documentation platform
- Community contributors

## 📞 Support

For issues or questions:

- Check [DOCUMENTATION.md](DOCUMENTATION.md) for detailed troubleshooting
- Open an issue on GitHub
- Contact: timvdhoorn

---

Made with ❤️ for the Open WebUI community
