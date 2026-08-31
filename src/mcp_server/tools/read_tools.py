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
        return await db.find_products(name_or_sku)

    @mcp.tool()
    async def get_stock(
        product_id: Annotated[str, Field(description="Product ID to get stock for")]
    ) -> dict | None:
        """Get stock and details for a specific product"""
        return await db.get_stock(product_id)

    @mcp.tool()
    async def get_low_stock_products(
        limit: Annotated[int, Field(description="Number of low stock products to get")] = 10
    ) -> list[dict]:
        """Get products with low stock level"""
        return await db.get_low_stock_products(limit)

    @mcp.tool()
    async def get_transactions_limit(
        limit: Annotated[int, Field(description="Number of recent transactions to get")] = 10
    ) -> list[dict]:
        """Get recent stock transactions history"""
        return await db.get_transactions_limit(limit)
