from typing import Annotated
from pydantic import Field
from src.mcp_server import db


def register_read_tools(mcp):
    """Đăng ký các read tools vào MCPServer instance."""

    @mcp.tool()
    async def find_products(
        name_or_sku: Annotated[str, Field(description="Name or SKU of products to find")]
    ) -> list[dict]:
        """Find products by name or SKU"""
        print(f"🔍 [MCP Tool: find_products] Tìm kiếm với từ khóa: '{name_or_sku}'")
        res = await db.find_products(name_or_sku)
        print(f"   ↳ Tìm thấy {len(res)} sản phẩm phù hợp.")
        return res

    @mcp.tool()
    async def get_stock(
        product_id: Annotated[str, Field(description="Product ID to get stock for")]
    ) -> dict | None:
        """Get stock and details for a specific product"""
        print(f"📦 [MCP Tool: get_stock] Xem chi tiết tồn kho: product_id='{product_id}'")
        return await db.get_stock(product_id)

    @mcp.tool()
    async def get_low_stock_products(
        limit: Annotated[int, Field(description="Number of low stock products to get")] = 10
    ) -> list[dict]:
        """Get products with low stock level"""
        print(f"⚠️ [MCP Tool: get_low_stock_products] Lấy danh sách hàng sắp hết (limit={limit})")
        res = await db.get_low_stock_products(limit)
        print(f"   ↳ Phát hiện {len(res)} mặt hàng dưới ngưỡng tối thiểu.")
        return res

    @mcp.tool()
    async def get_transactions_limit(
        limit: Annotated[int, Field(description="Number of recent transactions to get")] = 10
    ) -> list[dict]:
        """Get recent stock transactions history"""
        print(f"📜 [MCP Tool: get_transactions_limit] Lấy lịch sử {limit} giao dịch gần nhất")
        return await db.get_transactions_limit(limit)
