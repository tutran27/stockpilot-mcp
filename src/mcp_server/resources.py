from src.mcp_server import db


def register_resources(mcp):
    """Đăng ký các MCP Resources vào MCPServer instance."""

    @mcp.resource("stock://summary/realtime")
    async def get_realtime_summary() -> str:
        """Báo cáo tóm tắt tổng quan kho hàng thời gian thực (Tổng SKU, tổng tồn, cảnh báo thấp)"""
        print("[Resource] Đang đọc resource: stock://summary/realtime")
        products = await db.get_list_products(limit=100)
        low_stock = await db.get_low_stock_products(limit=100)
        total_quantity = sum(p["current_quantity"] for p in products)

        report = (
            "📊 **BÁO CÁO TỔNG QUAN TỒN KHO (REAL-TIME)**\n"
            f"- **Tổng số mặt hàng đang quản lý:** {len(products)} SKU\n"
            f"- **Tổng lượng hàng tồn kho:** {total_quantity} đơn vị\n"
            f"- **Số mặt hàng dưới ngưỡng an toàn:** {len(low_stock)} mặt hàng\n\n"
        )
        if low_stock:
            report += "⚠️ **DANH SÁCH HÀNG CẦN BỔ SUNG NGAY:**\n"
            for p in low_stock:
                report += f"- `{p['sku']}`: **{p['name']}** (Hiện còn: {p['current_quantity']} {p['unit']} / Tối thiểu: {p['minimum_quantity']} {p['unit']})\n"
        else:
            report += "✅ Mọi mặt hàng đều đang ở mức tồn an toàn."

        return report

    @mcp.resource("stock://policy/safety")
    def get_warehouse_policy() -> str:
        """Quy định & chính sách kiểm soát an toàn kho hàng"""
        print("[Resource] Đang đọc resource: stock://policy/safety")
        return (
            "📋 **QUY CHUẨN AN TOÀN VÀ VẬN HÀNH KHO HÀNG (SOP):**\n\n"
            "1. **Mức tồn kho an toàn:**\n"
            "   - Mọi mặt hàng khi số lượng tồn kho $\le$ mức tối thiểu (`minimum_quantity`) bắt buộc phải được lập kế hoạch bổ sung trong vòng 24h.\n\n"
            "2. **Quy trình Nhập kho (`receive_stock`):**\n"
            "   - Bắt buộc kiểm tra tem nhãn, chứng từ/hóa đơn đối tác trước khi xác nhận nhập.\n"
            "   - Giao dịch phải có `partner` (Nhà cung cấp) và `reference_notes` (Số hóa đơn).\n\n"
            "3. **Quy trình Xuất kho (`issue_stock`):**\n"
            "   - Không được phép xuất âm kho. Số lượng xuất phải $\le$ số lượng tồn khả dụng.\n\n"
            "4. **Kiểm soát thay đổi nhạy cảm (Human-in-the-loop):**\n"
            "   - Mọi thao tác thêm sản phẩm mới, nhập kho và xuất kho bắt buộc phải được Thủ kho xác nhận duyệt (CONFIRMED)."
        )
