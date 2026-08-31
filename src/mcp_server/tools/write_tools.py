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
        print(f"➕ [MCP Tool: add_product] Thêm sản phẩm mới: SKU='{sku}', Tên='{name}', ĐVT='{unit}', SL ban đầu={current_quantity}, Min={minimum_quantity}")
        res = await db.add_product(sku, name, unit, current_quantity, minimum_quantity)
        print(f"   ↳ Thêm sản phẩm thành công (id={res.get('id') if res else None})")
        return res

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
        print(f"📥 [MCP Tool: receive_stock] Thực thi Nhập kho: product_id='{product_id}', SL=+{quantity}, Đối tác='{partner}', HĐ='{reference_notes}'")
        await db.receive_stock(product_id, quantity, partner, reference_notes, note, idempotency_key)
        print(f"   ↳ Nhập kho thành công cho product_id='{product_id}'")
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
        print(f"📤 [MCP Tool: issue_stock] Thực thi Xuất kho: product_id='{product_id}', SL=-{quantity}, Đối tác='{partner}', HĐ='{reference_notes}'")
        await db.issue_stock(product_id, quantity, partner, reference_notes, note, idempotency_key)
        print(f"   ↳ Xuất kho thành công cho product_id='{product_id}'")
        return "Stock issued successfully"