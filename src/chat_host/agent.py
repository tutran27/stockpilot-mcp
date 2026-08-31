import json
from dotenv import load_dotenv
from mcp import Client

from src.mcp_server import db
from src.mcp_server.server import mcp
from src.chat_host.llm import call_llm
from src.chat_host.prompts import get_system_prompt
from src.chat_host.confirmation import create_pending_action, CONFIRMATION_REQUIRED_TOOLS
from src.chat_host.memory import update_working_context, format_working_context_prompt

load_dotenv()


async def run_agent(user_message: str, session_id: str = "default", chat_history: list[dict] | None = None) -> str:
    """
    Vòng lặp Agent điều phối:
    1. Tải Working State & N tin nhắn gần nhất từ Database.
    2. Ghép Context: System Prompt + Working State + Recent Buffer.
    3. Tự động cập nhật State từ tham số Tool và thực thi Tool.
    4. Lưu vết tin nhắn vào session history trong DB.
    """
    session_data = await db.get_or_create_session(session_id)
    working_context = session_data.get("working_context", {})

    if chat_history is None:
        chat_history = await db.get_recent_messages(session_id, limit=6)

    async with Client(mcp) as client:
        # Xử lý Slash Commands để nạp MCP Prompts tự động
        trimmed_msg = user_message.strip()
        if trimmed_msg.startswith("/audit"):
            prompt_res = await client.get_prompt("daily_audit_prompt")
            user_message = prompt_res.messages[0].content.text
        elif trimmed_msg.startswith("/restock"):
            parts = trimmed_msg.split(maxsplit=1)
            supplier = parts[1].strip() if len(parts) > 1 else "Dell"
            prompt_res = await client.get_prompt("restock_plan_prompt", arguments={"supplier_name": supplier})
            user_message = prompt_res.messages[0].content.text

        mcp_tools = await client.list_tools()
        openai_tools = [
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description or "",
                    "parameters": tool.input_schema,
                },
            }
            for tool in mcp_tools.tools
        ]

        # Ghép Prompt kèm Working State
        system_content = get_system_prompt()
        context_note = format_working_context_prompt(working_context)
        if context_note:
            system_content += "\n" + context_note

        messages: list[dict] = [{"role": "system", "content": system_content}]
        if chat_history:
            messages.extend(chat_history)
        messages.append({"role": "user", "content": user_message})

        max_turns = 5
        for _ in range(max_turns):
            response_msg = await call_llm(messages=messages, tools=openai_tools)

            if not response_msg.tool_calls:
                final_reply = response_msg.content or "Tôi không thể tạo câu trả lời vào lúc này."
                await db.save_message(session_id, "user", user_message)
                await db.save_message(session_id, "assistant", final_reply)
                return final_reply

            messages.append(response_msg)
            for tool_call in response_msg.tool_calls:
                tool_name = tool_call.function.name
                tool_args = json.loads(tool_call.function.arguments or "{}")

                # Tự động cập nhật State theo Declarative Mapping
                working_context = update_working_context(working_context, tool_name, tool_args)
                await db.update_session_working_context(session_id, working_context)

                if tool_name in CONFIRMATION_REQUIRED_TOOLS:
                    action_id = await create_pending_action(tool_name, tool_args)
                    working_context["last_action_id"] = action_id
                    await db.update_session_working_context(session_id, working_context)

                    reply = (
                        f"⚠️ Thao tác `{tool_name}` cần bạn xác nhận trước khi thực hiện.\n"
                        f"Mã hành động: `{action_id}`\n"
                        f"Chi tiết: {tool_args}"
                    )
                    await db.save_message(session_id, "user", user_message)
                    await db.save_message(session_id, "assistant", reply)
                    return reply

                print(f"  🤖 [Agent] Gọi Tool: {tool_name}({tool_args})")
                tool_res = await client.call_tool(name=tool_name, arguments=tool_args)

                texts = [c.text for c in tool_res.content if hasattr(c, "text")]
                content_str = "\n".join(texts) if texts else str(tool_res.content)

                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": content_str,
                    }
                )

        timeout_reply = "Đã đạt giới hạn số lượt gọi công cụ mà chưa có câu trả lời cuối cùng."
        await db.save_message(session_id, "user", user_message)
        await db.save_message(session_id, "assistant", timeout_reply)
        return timeout_reply


if __name__ == "__main__":
    import asyncio

    async def main():
        print("🤖 StockPilot Agent đã sẵn sàng!\n")
        test_questions = [
            "Trong kho hiện có những mặt hàng nào của hãng Dell?",
            "Kiểm tra xem có mặt hàng nào đang sắp hết không?",
            "Tôi muốn nhập thêm 10 cái Laptop Dell XPS 13 từ nhà cung cấp FPT, số HĐ: FPT-1234. Ghi chú: nhập lô mới",
        ]
        for q in test_questions:
            print(f"👤 User: {q}")
            answer = await run_agent(q)
            print(f"🤖 StockPilot:\n{answer}\n")
            print("-" * 60)

    asyncio.run(main())
