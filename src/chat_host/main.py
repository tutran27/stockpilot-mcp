import os
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from src.chat_host.agent import run_agent
from src.chat_host.confirmation import confirm_action, cancel_action
from src.mcp_server.server import mcp
from src.mcp_server import db

load_dotenv()

mcp_http_app = mcp.streamable_http_app(streamable_http_path="/")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await db.init_db()
    async with mcp.session_manager.run():
        yield
    await db.close_db()


app = FastAPI(title="StockPilot API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/mcp", mcp_http_app)


class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None


class ChatResponse(BaseModel):
    response: str
    session_id: str | None = None


class ConfirmRequest(BaseModel):
    action_id: str


@app.get("/health")
async def health_check():
    return {
        "status": "ok",
        "service": "StockPilot Chat Host",
        "version": "1.0.0",
    }


@app.post("/api/chat", response_model=ChatResponse)
async def chat_endpoint(req: ChatRequest):
    if not req.message.strip():
        raise HTTPException(status_code=400, detail="Tin nhắn không được để trống.")

    try:
        agent_reply = await run_agent(user_message=req.message)
        return ChatResponse(
            response=agent_reply,
            session_id=req.session_id,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/chat/confirm")
async def confirm_endpoint(req: ConfirmRequest):
    result = await confirm_action(action_id=req.action_id)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("message"))
    return result


@app.post("/api/chat/cancel")
async def cancel_endpoint(req: ConfirmRequest):
    result = await cancel_action(action_id=req.action_id)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("message"))
    return result


@app.get("/api/resources")
async def list_resources_endpoint():
    """Lấy danh sách các MCP Resources có sẵn."""
    from mcp import Client
    async with Client(mcp) as client:
        res = await client.list_resources()
        return [
            {
                "uri": str(r.uri),
                "name": r.name or str(r.uri),
                "description": r.description or "",
            }
            for r in res.resources
        ]


@app.get("/api/resources/read")
async def read_resource_endpoint(uri: str):
    """Đọc nội dung một MCP Resource theo URI."""
    from mcp import Client
    async with Client(mcp) as client:
        try:
            res = await client.read_resource(uri)
            content = res.contents[0].text if res.contents else ""
            return {"uri": uri, "content": content}
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/prompts")
async def list_prompts_endpoint():
    """Lấy danh sách các MCP Prompts có sẵn."""
    from mcp import Client
    async with Client(mcp) as client:
        res = await client.list_prompts()
        return [
            {
                "name": p.name,
                "description": p.description or "",
                "arguments": [
                    {"name": a.name, "description": a.description or "", "required": a.required}
                    for a in (p.arguments or [])
                ],
            }
            for p in res.prompts
        ]


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("CHAT_HOST_PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
