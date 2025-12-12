# Just for Demo 
from fastmcp import FastMCP
from mcp import app  # Import FastAPI app

# Convert FastAPI into MCP server
mcp = FastMCP.from_fastapi(
    app=app,
    name="Expense Tracker Server"
)

if __name__ == "__main__":
    mcp.run()