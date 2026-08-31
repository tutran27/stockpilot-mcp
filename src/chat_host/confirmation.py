import json
from datetime import datetime, timedelta
from mcp import Client
import uuid
from src.mcp_server.server import mcp
from src.mcp_server.db import get_pool

CONFIRMATION_REQUIRED_TOOLS = ["receive_stock", "issue_stock", "add_product"]

async def create_pending_action(
    tool_name: str,
    tool_arguments: dict,
    expire_minutes: int = 15,
) -> str:
    """Tạo một hành động chờ xác nhận trong Database và trả về action_id."""
    expires_at = datetime.utcnow() + timedelta(minutes=expire_minutes)
    session_id = str(uuid.uuid4())
    row = await get_pool().fetchrow(
        """
        INSERT INTO pending_actions (session_id, tool_name, tool_arguments, status, expires_at)
        VALUES ($1, $2, $3, 'PENDING', $4)
        RETURNING id;
        """,
        session_id,
        tool_name,
        json.dumps(tool_arguments),
        expires_at,
    )
    return str(row["id"])

async def get_pending_action(action_id: str) -> dict | None:
    """Lấy thông tin hành động chờ xác nhận theo ID."""
    row = await get_pool().fetchrow(
        """
        SELECT id, session_id, tool_name, tool_arguments, status, expires_at, created_at
        FROM pending_actions
        WHERE id = $1::uuid;
        """,
        action_id,
    )
    if not row:
        return None

    data = dict(row)
    data["id"] = str(data["id"])
    if isinstance(data["tool_arguments"], str):
        data["tool_arguments"] = json.loads(data["tool_arguments"])
    return data


async def confirm_action(action_id: str) -> dict:
    """Xác nhận và thực thi hành động đã chờ."""
    action = await get_pending_action(action_id)
    if not action:
        return {
            "success": False,
            "message": f"Không tìm thấy yêu cầu xác nhận: {action_id}",
        }

    if action["status"] != "PENDING":
        return {
            "success": False,
            "message": f"Yêu cầu này đã ở trạng thái {action['status']}, không thể xác nhận lại.",
        }

    if datetime.utcnow() > action["expires_at"]:
        await get_pool().execute(
            "UPDATE pending_actions SET status = 'EXPIRED' WHERE id = $1::uuid;",
            action_id,
        )
        return {
            "success": False,
            "message": "Yêu cầu xác nhận đã hết thời gian hiệu lực.",
        }

    tool_name = action["tool_name"]
    tool_args = action["tool_arguments"]
    if isinstance(tool_args, str):
        tool_args = json.loads(tool_args)

    async with Client(mcp) as client:
        tool_res = await client.call_tool(name=tool_name, arguments=tool_args)
        texts = [c.text for c in tool_res.content if hasattr(c, "text")]
        result_text = "\n".join(texts) if texts else str(tool_res.content)

        await get_pool().execute(
            "UPDATE pending_actions SET status = 'CONFIRMED' WHERE id = $1::uuid;",
            action_id,
        )

    return {
        "success": True,
        "action_id": action_id,
        "tool_name": tool_name,
        "result": result_text,
        "message": "Đã xác nhận và thực thi hành động thành công!",
    }


async def cancel_action(action_id: str) -> dict:
    """Hủy bỏ hành động chờ xác nhận."""
    action = await get_pending_action(action_id)
    if not action:
        return {
            "success": False,
            "message": f"Không tìm thấy yêu cầu xác nhận: {action_id}",
        }

    if action["status"] != "PENDING":
        return {
            "success": False,
            "message": f"Yêu cầu này đã ở trạng thái {action['status']}, không thể hủy.",
        }

    await get_pool().execute(
        "UPDATE pending_actions SET status = 'CANCELLED' WHERE id = $1::uuid;",
        action_id,
    )

    return {
        "success": True,
        "action_id": action_id,
        "message": "Đã hủy bỏ yêu cầu thực hiện hành động thành công.",
    }
