from contextlib import asynccontextmanager
from mcp.server.mcpserver import MCPServer
from src.mcp_server import db
from src.mcp_server.tools.read_tools import register_read_tools
from src.mcp_server.tools.write_tools import register_write_tools
from src.mcp_server.resources import register_resources
from src.mcp_server.prompts import register_prompts


@asynccontextmanager
async def lifespan(server: MCPServer):
    await db.init_db()
    yield


mcp = MCPServer(
    name="stockpilot",
    lifespan=lifespan,
)

# Đăng ký các Tools, Resources và Prompts vào MCP Server
register_read_tools(mcp)
register_write_tools(mcp)
register_resources(mcp)
register_prompts(mcp)


if __name__ == "__main__":
    mcp.run()
