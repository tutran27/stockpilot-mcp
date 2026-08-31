from dotenv import load_dotenv
from mcp import Client
from src.mcp_server.server import mcp

load_dotenv()


async def get_tools() -> list[dict]:
    """
    Lấy danh sách các tool từ MCP Server và chuyển sang định dạng OpenAI Function Calling.
    """
    async with Client(mcp) as client:
        result = await client.list_tools()
        return [
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description or "",
                    "parameters": tool.input_schema,
                },
            }
            for tool in result.tools
        ]


async def call_tool(name: str, arguments: dict) -> str:
    """
    Thực thi một tool trên MCP Server và trả về kết quả dạng text.
    """
    async with Client(mcp) as client:
        result = await client.call_tool(name=name, arguments=arguments)
        texts = [c.text for c in result.content if hasattr(c, "text")]
        return "\n".join(texts) if texts else str(result.content)


# ==============================================================================
# Script chạy thử nghiệm nhanh (Chạy: python -m src.chat_host.mcp_client)
# ==============================================================================
if __name__ == "__main__":
    import asyncio

    async def main():
        # 1. Lấy danh sách tools
        tools = await get_tools()
        print(f"✅ Đã load thành công {len(tools)} tools sang OpenAI format:")
        for t in tools:
            print(f"  - 🛠️ {t['function']['name']}: {t['function']['description']}")

        # 2. Test gọi 1 tool tra cứu kho
        print("\n🧪 Thử nghiệm gọi tool 'find_products' với từ khóa 'Dell':")
        res = await call_tool("find_products", {"name_or_sku": "Dell"})
        print("Kết quả trả về:")
        print(res)

    asyncio.run(main())