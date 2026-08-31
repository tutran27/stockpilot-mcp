import os
import re
import httpx
import streamlit as st

API_URL = os.getenv("API_URL", "http://localhost:8000")

st.set_page_config(
    page_title="StockPilot — Trợ lý Quản lý Kho MCP",
    page_icon="📦",
    layout="wide",
)

st.title("📦 StockPilot — AI Inventory Assistant (MCP)")
st.caption("Trợ lý kho thông minh tích hợp Model Context Protocol (Tools, Resources & Prompts)")

# Khởi tạo session state
if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": "Xin chào! Tôi là **StockPilot**, trợ lý kho ứng dụng chuẩn MCP. Bạn có thể hỏi tự nhiên, dùng các lệnh `/audit`, `/restock <NCC>`, hoặc chọn kịch bản ở thanh bên trái.",
        }
    ]

# Sidebar
with st.sidebar:
    st.header("⚙️ Trạng thái hệ thống")
    
    # Kiểm tra kết nối Backend API
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
    st.subheader("📖 MCP Resources (Tài nguyên tĩnh/động)")

    with st.expander("📊 Báo cáo kho Realtime (`stock://summary/realtime`)"):
        if st.button("Đọc dữ liệu Realtime", key="read_summary_btn", use_container_width=True):
            try:
                res = httpx.get(f"{API_URL}/api/resources/read", params={"uri": "stock://summary/realtime"}, timeout=5.0)
                if res.status_code == 200:
                    st.markdown(res.json().get("content", ""))
                else:
                    st.error("Không thể đọc resource.")
            except Exception as e:
                st.error(f"Lỗi: {e}")

    with st.expander("📋 Quy chuẩn kho (`stock://policy/safety`)"):
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
    if st.button("🗑️ Xóa lịch sử chat", use_container_width=True):
        st.session_state.messages = [
            {
                "role": "assistant",
                "content": "Lịch sử trò chuyện đã được làm mới. Tôi có thể giúp gì cho bạn?",
            }
        ]
        st.rerun()


# Hàm gửi request chat đến API
def send_chat_message(message_text: str):
    st.session_state.messages.append({"role": "user", "content": message_text})
    with st.chat_message("user"):
        st.markdown(message_text)

    with st.chat_message("assistant"):
        with st.spinner("🤖 Agent đang xử lý qua MCP Protocol..."):
            try:
                response = httpx.post(
                    f"{API_URL}/api/chat",
                    json={"message": message_text},
                    timeout=35.0,
                )
                if response.status_code == 200:
                    reply = response.json().get("response", "Không có phản hồi.")
                else:
                    reply = f"❌ Lỗi từ server: {response.text}"
            except Exception as e:
                reply = f"❌ Lỗi kết nối tới API: {e}"

            st.markdown(reply)
            st.session_state.messages.append({"role": "assistant", "content": reply})
            st.rerun()


# Hàm xử lý xác nhận hoặc hủy thao tác
def handle_action_confirmation(action_id: str, is_confirm: bool):
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
                data = res.json()
                msg = f"✅ **{data.get('message', 'Thành công!')}**\n\n- Mã hành động: `{action_id}`"
                if "result" in data:
                    msg += f"\n- Kết quả: `{data['result']}`"
            else:
                msg = f"❌ Lỗi {action_text}: {res.json().get('detail', res.text)}"
        except Exception as e:
            msg = f"❌ Lỗi kết nối: {e}"

    st.session_state.messages.append({"role": "assistant", "content": msg})
    st.rerun()


# Hiển thị lịch sử chat
for idx, msg in enumerate(st.session_state.messages):
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

        # Kiểm tra nếu phản hồi của Agent có chứa action_id cần xác nhận
        if msg["role"] == "assistant":
            match = re.search(r"Mã hành động:\s*`?([a-f0-9\-]{36})`?", msg["content"])
            if match:
                action_id = match.group(1)
                st.markdown("---")
                st.write("👉 **Vui lòng chọn hành động:**")
                col1, col2, _ = st.columns([1, 1, 3])
                with col1:
                    if st.button("🟢 Xác nhận thực hiện", key=f"confirm_{idx}_{action_id}"):
                        handle_action_confirmation(action_id, is_confirm=True)
                with col2:
                    if st.button("🔴 Hủy bỏ", key=f"cancel_{idx}_{action_id}"):
                        handle_action_confirmation(action_id, is_confirm=False)


# Xử lý input từ người dùng
user_input = st.chat_input("Nhập yêu cầu, hoặc gõ /audit, /restock <Tên NCC>...")

if "user_query" in st.session_state and st.session_state.user_query:
    query = st.session_state.user_query
    st.session_state.user_query = None
    send_chat_message(query)
elif user_input:
    send_chat_message(user_input)
