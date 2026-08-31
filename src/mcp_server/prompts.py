def register_prompts(mcp):
    """Đăng ký các MCP Prompts vào MCPServer instance."""

    @mcp.prompt()
    def daily_audit_prompt() -> str:
        """Kịch bản kiểm toán toàn diện tình hình kho hàng cuối ngày và đề xuất nhập hàng"""
        print("[Prompt] Kích hoạt MCP Prompt: daily_audit_prompt")
        return (
            "Hãy đóng vai trò là Trưởng ban Kiểm toán kho StockPilot. "
            "Thực hiện quy trình kiểm toán kho toàn diện theo các bước sau:\n"
            "1. Gọi tool `get_low_stock_products(limit=20)` để rà soát toàn bộ các mặt hàng đang thiếu hoặc sắp hết.\n"
            "2. Gọi tool `get_transactions_limit(limit=10)` để nắm bắt các biến động nhập xuất gần nhất.\n"
            "3. Tổng hợp thành một Báo cáo Kiểm toán chi tiết (dạng bảng Markdown) đánh giá rủi ro thiếu hàng và đề xuất số lượng cần nhập thêm cho từng mặt hàng."
        )

    @mcp.prompt()
    def restock_plan_prompt(supplier_name: str = "Dell") -> str:
        """Kịch bản lập kế hoạch bổ sung hàng theo một Nhà cung cấp hoặc Hãng cụ thể"""
        print(f"[Prompt] Kích hoạt MCP Prompt: restock_plan_prompt(supplier_name='{supplier_name}')")
        return (
            f"Hãy đóng vai trò Quản lý Mua hàng. "
            f"1. Dùng tool `find_products('{supplier_name}')` để tra cứu toàn bộ danh mục sản phẩm của hãng/nhà cung cấp '{supplier_name}'.\n"
            f"2. Đánh giá số lượng tồn kho so với mức tối thiểu của từng món.\n"
            f"3. Lập phiếu đề xuất đặt hàng mới cho '{supplier_name}' bao gồm: Mã SKU, Tên sản phẩm, Tồn hiện tại, Số lượng đề xuất nhập thêm, và Ước tính mức độ ưu tiên."
        )
