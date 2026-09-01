import os
from dotenv import load_dotenv
from openai import AsyncOpenAI

load_dotenv()

# Lấy cấu hình từ biến môi trường
GROQ_BASE_URL = os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1")
DEFAULT_MODEL = os.getenv("LLM_MODEL", "openai/gpt-oss-20b")


def get_client() -> AsyncOpenAI:
    """Khởi tạo hoặc lấy OpenAI Client với API key từ biến môi trường."""
    api_key = os.getenv("GROQ_API_KEY") or os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError(
            "❌ Thiếu API Key! Hãy cấu hình biến môi trường GROQ_API_KEY (hoặc OPENAI_API_KEY) trong tab Variables trên Railway."
        )
    return AsyncOpenAI(
        api_key=api_key,
        base_url=GROQ_BASE_URL,
    )


async def call_llm(
    messages: list[dict],
    tools: list[dict] | None = None,
    model: str = DEFAULT_MODEL,
    temperature: float = 0.2,
):
    """
    Gửi prompt và danh sách tools sang Groq LLM (OpenAI-compatible).
    """
    client = get_client()
    kwargs = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
    }

    if tools:
        kwargs["tools"] = tools
        kwargs["tool_choice"] = "auto"

    response = await client.chat.completions.create(**kwargs)
    return response.choices[0].message


if __name__ == "__main__":
    import asyncio

    async def main():
        print(f"=== TEST MODEL: {DEFAULT_MODEL} ===\n")

        # -------------------------------------------------------------
        # Case 1: Khi KHÔNG truyền tools (tools = None)
        # -------------------------------------------------------------
        print("🔹 [Case 1] Gửi câu hỏi thông thường (tools = None):")
        msg_no_tools = await call_llm(
            messages=[
                {"role": "system", "content": "Bạn là trợ lý quản lý kho thông minh StockPilot."},
                {"role": "user", "content": "Hãy giới thiệu ngắn gọn trong 1 câu về bạn."},
            ],
            tools=None,
        )
        print("--- [ORIGINAL MESSAGE OBJECT] ---")
        print(msg_no_tools.model_dump_json(indent=2))
        print("---------------------------------\n")

        # -------------------------------------------------------------
        # Case 2: Khi CÓ truyền tools (LLM tự quyết định gọi tool)
        # -------------------------------------------------------------
        sample_tools = [
            {
                "type": "function",
                "function": {
                    "name": "get_stock",
                    "description": "Tra cứu số lượng tồn kho và thông tin chi tiết của một sản phẩm theo ID hoặc SKU",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "product_id": {
                                "type": "string",
                                "description": "Mã định danh hoặc SKU của sản phẩm, ví dụ: 'LAPTOP-DELL-01'",
                            }
                        },
                        "required": ["product_id"],
                    },
                },
            }
        ]

        print("🔹 [Case 2] Người dùng yêu cầu tra cứu kho + truyền danh sách tools:")
        user_prompt = "Kiểm tra tồn kho giùm tôi sản phẩm có mã LAPTOP-DELL-01"
        print(f"User: \"{user_prompt}\"")

        msg_with_tools = await call_llm(
            messages=[
                {"role": "system", "content": "Bạn là trợ lý quản lý kho StockPilot. Hãy sử dụng công cụ thích hợp khi được yêu cầu."},
                {"role": "user", "content": user_prompt},
            ],
            tools=sample_tools,
        )
        print("--- [ORIGINAL MESSAGE OBJECT] ---")
        print(msg_with_tools.model_dump_json(indent=2))
        print("---------------------------------")

        if msg_with_tools.tool_calls:
            tool_call = msg_with_tools.tool_calls[0]
            print(f"\n👉 LLM đã trích xuất gọi Tool: {tool_call.function.name}")
            print(f"👉 Tham số LLM tạo ra        : {tool_call.function.arguments}")

    asyncio.run(main())
