from typing import Annotated
from pydantic import Field
from src.mcp_server import db


def register_write_tools(mcp):
    """Đăng ký các write tools vào MCPServer instance."""

    @mcp.tool()
    async def add_product(
        sku: Annotated[str, Field(description="Product SKU code (unique)")],
        name: Annotated[str, Field(description="Product name")],
        unit: Annotated[str, Field(description="Unit of measurement (e.g. piece, box, kg)")],
        current_quantity: Annotated[int, Field(description="Initial stock quantity")] = 0,
        minimum_quantity: Annotated[int, Field(description="Minimum stock warning threshold")] = 5,
    ) -> dict | None:
        """Add a new product to inventory catalog"""
        return await db.add_product(sku, name, unit, current_quantity, minimum_quantity)

    @mcp.tool()
    async def receive_stock(
        product_id: Annotated[str, Field(description="Product ID to receive stock for")],
        quantity: Annotated[int, Field(gt=0, description="Quantity to receive (must be > 0)")],
        partner: Annotated[str, Field(description="Supplier or partner name")] = "",
        reference_notes: Annotated[str, Field(description="Invoice or reference note")] = "",
        note: Annotated[str, Field(description="Internal note")] = "",
        idempotency_key: Annotated[str, Field(description="Unique key to prevent duplicate calls")] = "",
    ) -> str:
        """Receive stock into inventory (increases current quantity and logs transaction)"""
        await db.receive_stock(product_id, quantity, partner, reference_notes, note, idempotency_key)
        return "Stock received successfully"

    @mcp.tool()
    async def issue_stock(
        product_id: Annotated[str, Field(description="Product ID to issue stock for")],
        quantity: Annotated[int, Field(gt=0, description="Quantity to issue (must be > 0)")],
        partner: Annotated[str, Field(description="Customer or partner name")] = "",
        reference_notes: Annotated[str, Field(description="Invoice or reference note")] = "",
        note: Annotated[str, Field(description="Internal note")] = "",
        idempotency_key: Annotated[str, Field(description="Unique key to prevent duplicate calls")] = "",
    ) -> str:
        """Issue stock out of inventory (checks availability, decreases quantity and logs transaction)"""
        await db.issue_stock(product_id, quantity, partner, reference_notes, note, idempotency_key)
        return "Stock issued successfully"