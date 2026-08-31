"""
================================================================================
🧠 STOCKPILOT — BỘ NHỚ NGỮ CẢNH SIÊU GỌN (IN-MEMORY WORKING STATE & BUFFER)
================================================================================
Mục đích:
- Quản lý Working State và Lịch sử trò chuyện trực tiếp trong RAM theo session_id.
- Đơn giản, tốc độ cao, không làm phức tạp hóa Database.
- Tự động trích xuất thực thể quan trọng từ Tool calls và chèn vào System Prompt.
================================================================================
"""

# 1. BẢNG QUY TẮC ÁNH XẠ KHAI BÁO (Tool param -> State key)
STATE_FIELD_MAPPINGS = {
    "receive_stock": {
        "partner": "active_partner",
        "reference_notes": "current_invoice",
        "product_id": "focused_product_id",
    },
    "issue_stock": {
        "partner": "active_customer",
        "reference_notes": "current_invoice",
        "product_id": "focused_product_id",
    },
    "add_product": {
        "sku": "focused_sku",
        "name": "focused_product_name",
    },
}

STATE_LABELS = {
    "focused_product_name": "Sản phẩm đang trao đổi",
    "focused_sku": "Mã SKU",
    "focused_product_id": "ID sản phẩm",
    "active_partner": "Nhà cung cấp / Đối tác",
    "active_customer": "Khách hàng nhận",
    "current_invoice": "Số chứng từ / Hóa đơn",
    "last_action_id": "Mã hành động gần nhất",
}

# 2. BỘ NHỚ LƯU TRỮ THEO PHIÊN TRONG RAM (IN-MEMORY SESSION STORE)
_SESSIONS: dict[str, dict] = {}


def get_session(session_id: str) -> dict:
    """Lấy hoặc khởi tạo session trong bộ nhớ RAM."""
    if session_id not in _SESSIONS:
        _SESSIONS[session_id] = {
            "working_context": {},
            "messages": [],
        }
    return _SESSIONS[session_id]


def clear_session(session_id: str) -> None:
    """Xóa bỏ session khỏi bộ nhớ."""
    _SESSIONS.pop(session_id, None)


def update_working_context(working_context: dict, tool_name: str, tool_args: dict) -> dict:
    """Tự động cập nhật State từ tham số gọi Tool."""
    mapping = STATE_FIELD_MAPPINGS.get(tool_name, {})
    for arg_name, state_key in mapping.items():
        val = tool_args.get(arg_name)
        if val is not None and str(val).strip() != "":
            working_context[state_key] = val
    return working_context


def format_working_context_prompt(working_context: dict) -> str:
    """Chuyển State thành đoạn ghi chú ngắn gọn để chèn vào System Prompt."""
    if not working_context:
        return ""

    lines = ["\n[📌 THÔNG TIN NGỮ CẢNH ĐANG LÀM VIỆC (WORKING STATE)]:"]
    for key, val in working_context.items():
        if val:
            label = STATE_LABELS.get(key, key)
            lines.append(f"- **{label}:** {val}")

    lines.append("*(Hãy ưu tiên sử dụng thông tin ngữ cảnh trên nếu người dùng dùng từ thay thế như 'sản phẩm đó', 'hóa đơn đó')*")
    return "\n".join(lines)
