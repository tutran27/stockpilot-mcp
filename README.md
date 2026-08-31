# 📦 StockPilot — AI-Powered Inventory Assistant with MCP

<p align="center">
  <img src="https://img.shields.io/badge/Author-TuTran27-blue?style=for-the-badge&logo=github" alt="Author" />
  <img src="https://img.shields.io/badge/Python-3.12+-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python Version" />
  <img src="https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white" alt="FastAPI" />
  <img src="https://img.shields.io/badge/Model_Context_Protocol-MCP-8A2BE2?style=for-the-badge" alt="MCP" />
  <img src="https://img.shields.io/badge/PostgreSQL-17-4169E1?style=for-the-badge&logo=postgresql&logoColor=white" alt="PostgreSQL" />
  <img src="https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white" alt="Docker" />
  <img src="https://img.shields.io/badge/LLM-Groq%20%2F%20OpenAI-FF7043?style=for-the-badge" alt="LLM Provider" />
</p>

<p align="center">
  <b>Trợ lý Quản lý Kho thông minh ứng dụng Model Context Protocol (MCP) & ReAct AI Agent với cơ chế Human-in-the-loop.</b>
</p>

---

## 📑 Mục lục (Table of Contents)
- [🌟 Giới thiệu dự án](#-giới-thiệu-dự-án-overview)
- [🎯 Những kiến thức cốt lõi về MCP trong repo](#-những-kiến-thức-cốt-lõi-về-mcp-trong-repo)
- [🏗️ Kiến trúc hệ thống (Architecture)](#️-kiến-trúc-hệ-thống-architecture)
- [🛠️ Danh mục MCP Tools](#️-danh-mục-mcp-tools)
- [📁 Cấu trúc thư mục](#-cấu-trúc-thư-mục-project-structure)
- [🚦 Hướng dẫn cài đặt & Chạy ứng dụng](#-hướng-dẫn-cài-đặt--chạy-ứng-dụng-quick-start)
- [🧪 Luồng trải nghiệm thực tế (Demo Flow)](#-luồng-trải-nghiệm-thực-tế-demo-flow)
- [📄 Bản quyền (License)](#-bản-quyền-license)

---

## 🌟 Giới thiệu dự án (Overview)

Chào bạn! 👋 

**StockPilot** là một dự án Hands-on Reference Project do mình xây dựng nhằm **thực hành, làm chủ và đào sâu chuẩn giao thức Model Context Protocol (MCP)** mới nhất của Anthropic.

Thay vì dừng lại ở các kịch bản demo đơn giản, **StockPilot** giải quyết một bài toán nghiệp vụ kinh doanh thực tế: **Quản lý kho hàng thông minh (Inventory Management)**. Hệ thống kết hợp sức mạnh của LLM (Groq / OpenAI) với khả năng tương tác cơ sở dữ liệu thật một cách an toàn thông qua các nguyên tắc:
* 🛡️ **Human-in-the-loop (HITL):** Xác nhận trước khi thực thi các thao tác nhạy cảm (nhập, xuất kho, tạo sản phẩm).
* ⚡ **ACID Transactions & Idempotency:** Đảm bảo toàn vẹn dữ liệu kho và chống trùng lặp giao dịch.
* 🔌 **Chuẩn giao thức MCP:** Kiến trúc tách biệt rõ ràng giữa **Chat Host**, **Client**, và **MCP Server**.

---

## 🎯 Những kiến thức cốt lõi về MCP trong repo

> [!NOTE]
> Dự án này đóng vai trò như một **Cheat Sheet thực chiến** dành cho bất kỳ ai muốn tìm hiểu cách xây dựng ứng dụng AI Agent kết nối MCP Server.

1. **Kiến trúc phân tầng MCP:** Hiểu rõ mối liên kết giữa **Host** (FastAPI) $\leftrightarrow$ **Client** (`mcp.Client`) $\leftrightarrow$ **Server** (`FastMCP`).
2. **Phân loại MCP Tools:**
   * **Read Tools (Safe):** Cho phép Agent tự do gọi để tra cứu, phân tích dữ liệu kho.
   * **Write Tools (Sensitive):** Được quản lý bởi hàng đợi `pending_actions`, yêu cầu người dùng xác nhận mới thực thi.
3. **Điều phối Vòng lặp Agent (ReAct Loop):** Tự động phát hiện `tool_calls` từ LLM, gọi Tool qua MCP Client, nạp kết quả vào context và sinh câu trả lời tự nhiên.
4. **Vận hành hạ tầng & Docker hóa:** Triển khai đồng bộ PostgreSQL 17, pgAdmin, và Chat Host qua Docker Compose với Healthcheck tự động.

---

## 🏗️ Kiến trúc hệ thống (Architecture)

```mermaid
flowchart TD
    User([👤 Người dùng / Quản kho]) <-->|REST API / Chat| Host[🌐 Chat Host / FastAPI]
    
    subgraph ChatHostApp ["Chat Host (Orchestrator)"]
        Host <--> Agent["🤖 ReAct Agent Loop"]
        Agent <--> LLM["🧠 LLM (Groq / OpenAI)"]
        Agent <--> HITL["🛡️ Human-in-the-loop Gate"]
        Agent <--> MCPClient["🔌 MCP Client"]
    end

    subgraph MCPServerApp ["MCP Server (StockPilot)"]
        MCPClient <==>|MCP Protocol (In-Memory / HTTP)| MCPServer["⚙️ FastMCP Server"]
        MCPServer --> ReadTools["📖 Read Tools (find, get_stock, alert)"]
        MCPServer --> WriteTools["✍️ Write Tools (receive, issue, add)"]
        ReadTools & WriteTools --> DBModule["💾 DB Layer (asyncpg)"]
    end

    DBModule <==>|Connection Pool| Postgres[(🐘 PostgreSQL Database)]
```

---

## 🛠️ Danh mục MCP Tools

### 📖 Read Tools (Tra cứu — An toàn, thực thi tự động)

| Tên Tool | Tham số | Mục đích |
| :--- | :--- | :--- |
| `find_products` | `name_or_sku: str` | Tìm kiếm sản phẩm theo tên hoặc mã SKU (tìm kiếm mờ `ILIKE`). |
| `get_stock` | `product_id: str` | Lấy chi tiết thông tin và tồn kho hiện tại theo ID sản phẩm. |
| `get_low_stock_products` | `limit: int = 10` | Cảnh báo danh sách sản phẩm có tồn kho $\le$ ngưỡng tối thiểu. |
| `get_transactions_limit` | `limit: int = 10` | Lấy lịch sử biến động kho gần nhất. |

### ✍️ Write Tools (Thao tác nhạy cảm — Kích hoạt Human-in-the-loop)

| Tên Tool | Tham số | Mục đích |
| :--- | :--- | :--- |
| `add_product` | `sku, name, unit, current_quantity, minimum_quantity` | Thêm mặt hàng mới vào danh mục kho. |
| `update_stock` | `product_id, quantity_delta` | Tăng/giảm trực tiếp tồn kho của sản phẩm. |
| `receive_stock` | `product_id, quantity, partner, reference_notes, note, idempotency_key` | **Nhập kho:** Tăng tồn kho và tự động ghi log giao dịch (`stock_transactions`). |
| `issue_stock` | `product_id, quantity, partner, reference_notes, note, idempotency_key` | **Xuất kho:** Kiểm tra đủ hàng, trừ tồn kho và ghi log giao dịch an toàn. |

---

## 📁 Cấu trúc thư mục (Project Structure)

```text
stockpilot/
├── 📄 compose.yaml             # Docker Compose cho PostgreSQL & pgAdmin
├── 📄 Dockerfile               # Dockerfile cho Chat Host
├── 📄 .dockerignore            # Loại trừ các file rác/bí mật khi build Docker
├── 📄 .gitignore               # Cấu hình bỏ qua git cho .venv, .env, cache
├── 📄 requirements.txt         # Danh sách thư viện Python
├── 📄 .env.example             # Template biến môi trường
├── 📄 README.md                # Tài liệu hướng dẫn dự án
│
├── 📁 db/                      # Cơ sở dữ liệu
│   └── init.sql                # Script khởi tạo bảng, quan hệ & index
│
├── 📁 scripts/                 # Scripts tiện ích
│   └── seed_products.py        # Nạp dữ liệu sản phẩm mẫu vào PostgreSQL
│
├── 📁 src/                     # Mã nguồn chính
│   ├── 📁 common/              # Cấu hình dùng chung
│   │   └── config.py
│   │
│   ├── 📁 mcp_server/          # ⚙️ MCP Server Layer
│   │   ├── server.py           # Khởi tạo FastMCP Server & Lifespan
│   │   ├── db.py               # Thao tác DB (Connection Pool, Transactions)
│   │   └── 📁 tools/
│   │       ├── read_tools.py   # Read Tools
│   │       └── write_tools.py  # Write Tools
│   │
│   └── 📁 chat_host/           # 🌐 Chat Host & Agent Orchestrator
│       ├── main.py             # FastAPI App & Endpoints (/api/chat, /confirm, /cancel)
│       ├── agent.py            # Vòng lặp Agent điều phối Tool Calling
│       ├── llm.py              # LLM Adapter (Groq / OpenAI)
│       ├── confirmation.py     # Quản lý xác nhận Human-in-the-loop
│       └── prompts.py          # System Prompts & Hướng dẫn nghiệp vụ cho Agent
│
└── 📁 tests/                   # Kiểm thử tự động
```

---

## 🚦 Hướng dẫn cài đặt & Chạy ứng dụng (Quick Start)

### Bước 1: Clone Repository & Cấu hình môi trường
```bash
# Clone repo
git clone https://github.com/tutran27/stockpilot-mcp.git
cd stockpilot-mcp

# Copy cấu hình mẫu
cp .env.example .env
```
> Chỉnh sửa file `.env` và điền `GROQ_API_KEY` (hoặc `OPENAI_API_KEY`).

### Bước 2: Khởi chạy PostgreSQL Database bằng Docker
```bash
docker compose up -d
```
* **PostgreSQL:** `localhost:5432`
* **pgAdmin Web UI:** [http://localhost:5050](http://localhost:5050) (Email: `admin@admin.com` | Password: `admin`)

### Bước 3: Cài đặt Dependencies & Nạp dữ liệu mẫu
```bash
# Tạo và kích hoạt môi trường ảo
python3 -m venv .venv
source .venv/bin/activate  # Trên Windows: .venv\Scripts\activate

# Cài đặt thư viện
pip install -r requirements.txt

# Nạp dữ liệu mẫu vào DB
python scripts/seed_products.py
```

### Bước 4: Khởi chạy Chat Host (FastAPI)
```bash
python -m src.chat_host.main
```
* **API Swagger Docs:** [http://localhost:8000/docs](http://localhost:8000/docs)

---

## 🧪 Luồng trải nghiệm thực tế (Demo Flow)

### 1️⃣ Tra cứu tồn kho (Safe Action -> Trả kết quả ngay)
Gửi yêu cầu qua `POST http://localhost:8000/api/chat`:
```json
{
  "message": "Trong kho hiện có những mặt hàng nào của hãng Dell?"
}
```
🤖 **Phản hồi từ Agent:**
> *"Trong kho hiện có các sản phẩm của Dell:*
> *1. Laptop Dell XPS 13 (SKU: DELL-XPS13) — Tồn kho: 15 cái*
> *2. Màn hình Dell UltraSharp 27 inch (SKU: DELL-U2724D) — Tồn kho: 8 cái"*

---

### 2️⃣ Thao tác nhạy cảm (Sensitive Action -> Kích hoạt Human-in-the-loop)

#### Bước 2.1: Gửi yêu cầu nhập hàng qua Chat
```json
{
  "message": "Tôi muốn nhập thêm 10 cái Laptop Dell XPS 13 từ NCC FPT, số HĐ: FPT-999. Ghi chú: nhập lô mới"
}
```
⚠️ **Agent phát hiện tool nhạy cảm và trả về mã xác nhận:**
```json
{
  "response": "⚠️ Thao tác `receive_stock` cần bạn xác nhận trước khi thực hiện.\nMã hành động: `e70ce90c-575f-4462-81ae-672a29b26fdc`\nChi tiết: {'product_id': '...', 'quantity': 10, 'partner': 'FPT', 'reference_notes': 'FPT-999'}",
  "session_id": null
}
```

#### Bước 2.2: Xác nhận thực hiện qua `POST http://localhost:8000/api/chat/confirm`
```json
{
  "action_id": "e70ce90c-575f-4462-81ae-672a29b26fdc"
}
```
✅ **Kết quả trả về:**
```json
{
  "success": true,
  "action_id": "e70ce90c-575f-4462-81ae-672a29b26fdc",
  "tool_name": "receive_stock",
  "result": "Stock received successfully",
  "message": "Đã xác nhận và thực thi hành động thành công!"
}
```

---

## 📄 Bản quyền (License)

Dự án được phân phối dưới giấy phép mã nguồn mở **MIT License**.
