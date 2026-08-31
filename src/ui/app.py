"""
================================================================================
📦 STOCKPILOT — GIAO DIỆN WEB CHAT STREAMLIT TÍCH HỢP MCP & MULTI-SESSION
================================================================================
Mục đích file:
- Cung cấp giao diện Web Chat tương tác với AI Agent quản lý kho.
- Hỗ trợ đa phiên trò chuyện (Multi-Session): Lưu lịch sử và chuyển đổi qua lại.
- Tự động ghi nhớ Working State (Mã SKU, Hóa đơn, NCC) và 6 tin nhắn gần nhất.
- Xử lý cơ chế Human-in-the-loop (HITL) xác nhận hành động trực quan.
================================================================================
"""

import os
import re
import ast
import json
import uuid
import httpx
import streamlit as st

# ==============================================================================
# PHẦN 1: CẤU HÌNH TRANG WEB & BIẾN MÔI TRƯỜNG
# ==============================================================================
API_URL = os.getenv("API_URL", "http://localhost:8000")

st.set_page_config(
    page_title="StockPilot — Trợ lý Quản lý Kho MCP",
    page_icon="📦",
    layout="wide",
)

# ==============================================================================
# PHẦN 2: KHỞI TẠO TRẠNG THÁI PHIÊN LÀM VIỆC (SESSION STATE)
# ==============================================================================
# 1. session_id: Định danh phiên trò chuyện hiện tại (Tự động cấp mới khi New Chat)
if "session_id" not in st.session_state:
    st.session_state.session_id = uuid.uuid4().hex[:10]

# 2. messages: Danh sách lưu trữ lịch sử tin nhắn của phiên hiện tại
if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": f"Xin chào! Tôi là **StockPilot**, trợ lý kho ứng dụng chuẩn MCP. Bạn đang ở phiên `{st.session_state.session_id}`. Bạn có thể hỏi tự nhiên, tạo cuộc trò chuyện mới hoặc chọn phiên cũ ở thanh bên trái.",
        }
    ]

# 3. action_statuses: Dictionary lưu trạng thái của từng action_id
if "action_statuses" not in st.session_state:
    st.session_state.action_statuses = {}

# Tiêu đề và mô tả chính hiển thị ở đầu trang (Kèm mã Session ID trực quan)
st.title("📦 StockPilot — AI Inventory Assistant (MCP)")
st.caption(f"Trợ lý kho thông minh • 🆔 Phiên làm việc hiện tại: `{st.session_state.session_id}`")


# ==============================================================================
# PHẦN 3: HÀM BỔ TRỢ ĐỊNH DẠNG TIN NHẮN XÁC NHẬN (FORMAT CONFIRMATION DISPLAY)
# ==============================================================================
def format_confirmation_display(content: str) -> str:
    """Làm đẹp chuỗi dictionary thô từ Agent thành danh sách Markdown trực quan."""
    match = re.search(r"⚠️\s*Thao tác\s*`?([^`\n]+)`?\s*cần bạn xác nhận trước khi thực hiện\.", content)
    if not match:
        return content

    tool_name = match.group(1).strip()
    action_match = re.search(r"Mã hành động:\s*`?([a-f0-9\-]{36})`?", content)
    action_id = action_match.group(1) if action_match else ""

    details_match = re.search(r"Chi tiết:\s*({.*})", content, re.DOTALL)
    tool_args = {}
    if details_match:
        raw_dict_str = details_match.group(1).strip()
        try:
            tool_args = ast.literal_eval(raw_dict_str)
        except Exception:
            try:
                tool_args = json.loads(raw_dict_str.replace("'", '"'))
            except Exception:
                tool_args = {}

    tool_display_names = {
        "receive_stock": "📥 Nhập kho (`receive_stock`)",
        "issue_stock": "📤 Xuất kho (`issue_stock`)",
        "add_product": "✨ Thêm sản phẩm mới (`add_product`)",
    }
    action_label = tool_display_names.get(tool_name, f"⚡ `{tool_name}`")

    friendly_labels = {
        "product_id": "📦 Mã sản phẩm (ID)",
        "quantity": "🔢 Số lượng",
        "partner": "🏢 Đối tác / Nhà cung cấp",
        "reference_notes": "🧾 Mã chứng từ / Hóa đơn",
        "note": "📝 Ghi chú",
        "sku": "🔖 Mã SKU",
        "name": "🏷️ Tên sản phẩm",
        "unit": "📏 Đơn vị tính",
    }

    lines = [
        f"⚠️ **Yêu cầu xác nhận thao tác:** {action_label}",
        f"- **Mã hành động:** `{action_id}`",
        "- **Thông tin chi tiết:**",
    ]

    if tool_args:
        for k, v in tool_args.items():
            label = friendly_labels.get(k, f"• {k}")
            if k == "quantity" and tool_name == "receive_stock":
                lines.append(f"  - {label}: **+{v}**")
            elif k == "quantity" and tool_name == "issue_stock":
                lines.append(f"  - {label}: **-{v}**")
            else:
                lines.append(f"  - {label}: `{v}`" if isinstance(v, str) and len(v) > 20 else f"  - {label}: {v}")
    else:
        lines.append(f"  - {content}")

    return "\n".join(lines)


# ==============================================================================
# PHẦN 4: THANH ĐIỀU HƯỚNG BÊN CẠNH (SIDEBAR)
# ==============================================================================
with st.sidebar:
    # 4.1. Nút Tạo phiên trò chuyện mới (New Chat)
    if st.button("➕ Cuộc trò chuyện mới", use_container_width=True, type="primary"):
        st.session_state.session_id = uuid.uuid4().hex[:10]
        st.session_state.messages = [
            {
                "role": "assistant",
                "content": "Xin chào! Đây là phiên chat mới. Tôi có thể giúp gì cho bạn hôm nay?",
            }
        ]
        st.session_state.action_statuses = {}
        st.rerun()

    st.markdown("---")
    # 4.2. Danh sách các phiên trò chuyện cũ (Lịch sử phiên chat)
    st.subheader("💬 Lịch sử trò chuyện")
    try:
        sessions_res = httpx.get(f"{API_URL}/api/chat/sessions?limit=10", timeout=2.0)
        if sessions_res.status_code == 200:
            sessions_list = sessions_res.json().get("sessions", [])
            if sessions_list:
                for s in sessions_list:
                    s_id = s["id"]
                    s_title = s.get("title", "Cuộc trò chuyện mới")
                    display_title = (s_title[:26] + "...") if len(s_title) > 26 else s_title
                    is_current = (s_id == st.session_state.session_id)
                    btn_label = f"{'🟢 ' if is_current else '📄 '}{display_title}"
                    
                    if st.button(btn_label, key=f"sess_{s_id}", use_container_width=True, disabled=is_current):
                        # Tải lại toàn bộ lịch sử tin nhắn của phiên được chọn
                        detail_res = httpx.get(f"{API_URL}/api/chat/session/{s_id}", timeout=3.0)
                        if detail_res.status_code == 200:
                            data = detail_res.json()
                            raw_msgs = data.get("messages", [])
                            if raw_msgs:
                                st.session_state.messages = [
                                    {"role": m["role"], "content": m["content"]}
                                    for m in raw_msgs
                                ]
                            else:
                                st.session_state.messages = [
                                    {"role": "assistant", "content": "Phiên trò chuyện này chưa có tin nhắn."}
                                ]
                            st.session_state.session_id = s_id
                            st.session_state.action_statuses = {}
                            st.rerun()
            else:
                st.caption("Chưa có phiên trò chuyện nào.")
    except Exception:
        st.caption("Không thể tải danh sách phiên chat.")

    st.markdown("---")
    # 4.3. Xem dữ liệu Working State thời gian thực
    st.subheader("🧠 Bộ nhớ ngữ cảnh (Working State)")
    with st.expander("🔍 Xem dữ liệu State của phiên này", expanded=False):
        try:
            state_res = httpx.get(f"{API_URL}/api/chat/session/{st.session_state.session_id}", timeout=2.0)
            if state_res.status_code == 200:
                cur_ctx = state_res.json().get("working_context", {})
                if cur_ctx:
                    st.json(cur_ctx)
                else:
                    st.caption("Chưa có thông tin thực thể nào được ghi nhớ trong phiên này.")
            else:
                st.caption("Chưa có dữ liệu session.")
        except Exception:
            st.caption("Không thể kết nối lấy trạng thái State.")

    st.markdown("---")
    st.header("⚙️ Trạng thái hệ thống")
    try:
        res = httpx.get(f"{API_URL}/health", timeout=2.0)
        if res.status_code == 200:
            st.success(f"🟢 Backend API: Online ({API_URL})")
        else:
            st.warning(f"🟡 Backend API: Status {res.status_code}")
    except Exception:
        st.error(f"🔴 Không thể kết nối Backend API: {API_URL}")

    st.markdown("---")
    st.subheader("📝 MCP Prompts (Kịch bản mẫu)")
    if st.button("📊 Kích hoạt: /audit (Kiểm toán cuối ngày)", use_container_width=True):
        st.session_state.user_query = "/audit"

    supplier_input = st.text_input("Tên NCC/Hãng:", value="Dell", key="supplier_input")
    if st.button(f"📦 Kế hoạch đặt hàng: /restock {supplier_input}", use_container_width=True):
        st.session_state.user_query = f"/restock {supplier_input}"

    st.markdown("---")
    st.subheader("📖 MCP Resources (Tài nguyên)")
    with st.expander("📊 Báo cáo kho Realtime"):
        if st.button("Đọc dữ liệu Realtime", key="read_summary_btn", use_container_width=True):
            try:
                res = httpx.get(f"{API_URL}/api/resources/read", params={"uri": "stock://summary/realtime"}, timeout=5.0)
                if res.status_code == 200:
                    st.markdown(res.json().get("content", ""))
                else:
                    st.error("Không thể đọc resource.")
            except Exception as e:
                st.error(f"Lỗi: {e}")

    with st.expander("📋 Quy chuẩn an toàn kho"):
        if st.button("Đọc quy chuẩn an toàn", key="read_policy_btn", use_container_width=True):
            try:
                res = httpx.get(f"{API_URL}/api/resources/read", params={"uri": "stock://policy/safety"}, timeout=5.0)
                if res.status_code == 200:
                    st.markdown(res.json().get("content", ""))
                else:
                    st.error("Không thể đọc resource.")
            except Exception as e:
                st.error(f"Lỗi: {e}")

    st.markdown("---")
    st.subheader("💡 Câu hỏi mẫu")
    quick_queries = [
        "Trong kho hiện có những mặt hàng nào của Dell?",
        "Kiểm tra xem có mặt hàng nào đang sắp hết không?",
        "Lấy danh sách 5 giao dịch xuất nhập kho gần nhất.",
        "Tôi muốn nhập thêm 10 cái Laptop Dell XPS 13 từ NCC FPT, số HĐ: FPT-1234.",
    ]
    for q in quick_queries:
        if st.button(q, use_container_width=True):
            st.session_state.user_query = q

    st.markdown("---")
    # 4.4. Nút xóa phiên chat hiện tại khỏi Database
    if st.button("🗑️ Xóa phiên chat này", use_container_width=True):
        try:
            httpx.delete(f"{API_URL}/api/chat/session/{st.session_state.session_id}", timeout=3.0)
        except Exception:
            pass

        st.session_state.session_id = uuid.uuid4().hex[:10]
        st.session_state.messages = [
            {
                "role": "assistant",
                "content": "Phiên trò chuyện đã được xóa. Tôi có thể giúp gì cho bạn?",
            }
        ]
        st.session_state.action_statuses = {}
        st.rerun()


# ==============================================================================
# PHẦN 5: HÀM GỬI YÊU CẦU CHAT TỚI BACKEND API
# ==============================================================================
def send_chat_message(message_text: str):
    """Gửi câu hỏi kèm session_id tới FastAPI Backend."""
    st.session_state.messages.append({"role": "user", "content": message_text})
    with st.chat_message("user"):
        st.markdown(message_text)

    with st.chat_message("assistant"):
        with st.spinner("🤖 Agent đang xử lý qua MCP Protocol & Working State..."):
            try:
                response = httpx.post(
                    f"{API_URL}/api/chat",
                    json={
                        "message": message_text,
                        "session_id": st.session_state.session_id,
                    },
                    timeout=35.0,
                )
                if response.status_code == 200:
                    reply = response.json().get("response", "Không có phản hồi.")
                else:
                    reply = f"❌ Lỗi từ server: {response.text}"
            except Exception as e:
                reply = f"❌ Lỗi kết nối tới API: {e}"

            st.session_state.messages.append({"role": "assistant", "content": reply})
            st.rerun()


# ==============================================================================
# PHẦN 6: HÀM XỬ LÝ XÁC NHẬN HOẶC HỦY BỎ THAO TÁC (HITL)
# ==============================================================================
def handle_action_confirmation(action_id: str, is_confirm: bool):
    """Xử lý xác nhận hoặc hủy bỏ thao tác nhạy cảm."""
    endpoint = "confirm" if is_confirm else "cancel"
    action_text = "xác nhận" if is_confirm else "hủy bỏ"

    with st.spinner(f"Đang {action_text} thao tác..."):
        try:
            res = httpx.post(
                f"{API_URL}/api/chat/{endpoint}",
                json={"action_id": action_id},
                timeout=15.0,
            )
            if res.status_code == 200:
                st.session_state.action_statuses[action_id] = "confirmed" if is_confirm else "cancelled"
                data = res.json()
                action_type_str = "xác nhận và thực thi" if is_confirm else "hủy bỏ"
                msg = f"✅ **Đã {action_type_str} hành động thành công!**\n\n- **Mã hành động:** `{action_id}`"
                if "result" in data and data["result"]:
                    msg += f"\n- **Kết quả:** `{data['result']}`"
            else:
                err_detail = res.json().get("detail", res.text)
                if "CONFIRMED" in err_detail:
                    st.session_state.action_statuses[action_id] = "confirmed"
                elif "CANCELLED" in err_detail:
                    st.session_state.action_statuses[action_id] = "cancelled"
                msg = f"❌ **Lỗi {action_text}:** {err_detail}"
        except Exception as e:
            msg = f"❌ **Lỗi kết nối:** {e}"

    st.session_state.messages.append({"role": "assistant", "content": msg})
    st.rerun()


# ==============================================================================
# PHẦN 7: HIỂN THỊ LỊCH SỬ TIN NHẮN VÀ NÚT HÀNH ĐỘNG
# ==============================================================================
for idx, msg in enumerate(st.session_state.messages):
    with st.chat_message(msg["role"]):
        formatted_content = format_confirmation_display(msg["content"])
        st.markdown(formatted_content)

        if msg["role"] == "assistant" and ("cần bạn xác nhận" in msg["content"] or "Yêu cầu xác nhận" in msg["content"]):
            match = re.search(r"Mã hành động:\s*`?([a-f0-9\-]{36})`?", msg["content"])
            if match:
                action_id = match.group(1)
                status = st.session_state.action_statuses.get(action_id)

                st.markdown("---")
                if status == "confirmed":
                    st.caption("🔒 *Thao tác này đã được xác nhận thực hiện.*")
                elif status == "cancelled":
                    st.caption("🚫 *Thao tác này đã bị hủy bỏ.*")
                else:
                    st.write("👉 **Vui lòng chọn hành động:**")
                    col1, col2, _ = st.columns([1, 1, 2])
                    with col1:
                        if st.button("🟢 Xác nhận thực hiện", key=f"confirm_{idx}_{action_id}", use_container_width=True):
                            handle_action_confirmation(action_id, is_confirm=True)
                    with col2:
                        if st.button("🔴 Hủy bỏ", key=f"cancel_{idx}_{action_id}", use_container_width=True):
                            handle_action_confirmation(action_id, is_confirm=False)


# ==============================================================================
# PHẦN 8: XỬ LÝ Ô NHẬP LIỆU CHAT TỪ NGƯỜI DÙNG
# ==============================================================================
user_input = st.chat_input("Nhập yêu cầu, hoặc gõ /audit, /restock <Tên NCC>...")

if "user_query" in st.session_state and st.session_state.user_query:
    query = st.session_state.user_query
    st.session_state.user_query = None
    send_chat_message(query)
elif user_input:
    send_chat_message(user_input)
