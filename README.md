# Trackor

This is a custom MCP (Model Context Protocol) server built with **FastMCP**.  
It provides tools to track expenses, including adding, listing, summarizing, updating, and exporting data.

The server uses a local SQLite database (`expenses.db`) and a `categories.json` file for expense categories.
## Local Development (using uv)

Install dependencies:

```bash
uv sync
```

Run MCP server:

```bash
uv run mcp.py
```