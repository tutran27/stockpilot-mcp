import os
from dotenv import load_dotenv

load_dotenv()

# Database
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/stockpilot",
)

# LLM
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
LLM_MODEL = os.getenv("LLM_MODEL", "openai/gpt-oss-20b")
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://api.groq.com/openai/v1")

# Server & Host Ports
CHAT_HOST_PORT = int(os.getenv("CHAT_HOST_PORT", 8000))
MCP_SERVER_PORT = int(os.getenv("MCP_SERVER_PORT", 8001))
MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", f"http://127.0.0.1:{CHAT_HOST_PORT}/mcp")
