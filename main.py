from fastapi import FastAPI, HTTPException
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel
from typing import Dict, Any
from datetime import datetime, timezone
from strands import Agent
from agents.supervisor import SupervisorAgent
import random

app = FastAPI(title="re:Invent Attendee Guide Agent Server", version="1.0.0")

# Initialize Strands agent
# strands_agent = Agent()


class InvocationRequest(BaseModel):
    input: Dict[str, Any]


class InvocationResponse(BaseModel):
    output: Dict[str, Any]


# initialize Agent
session_id = str(random.randint(100000000, 999999999))
attendee_guide_agent = SupervisorAgent(session_id=f"session_{session_id}")


@app.post("/invocations", response_model=InvocationResponse)
async def invoke_agent(request: InvocationRequest):
    try:
        user_message = request.input.get("prompt", "")
        if not user_message:
            raise HTTPException(
                status_code=400,
                detail="No prompt found in input. Please provide a 'prompt' key in the input.",
            )

        result = attendee_guide_agent.process_message(user_message)
        response = {
            "message": result,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "model": "strands-agent",
        }

        return InvocationResponse(output=response)

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Agent processing failed: {str(e)}"
        )


@app.post("/invocations/markdown", response_class=PlainTextResponse)
async def invoke_agent_markdown(request: InvocationRequest):
    """
    返回 Markdown 格式的响应，可直接保存为 .md 文件
    
    使用示例:
    curl -X POST http://your-api/invocations/markdown \
    -H "Content-Type: application/json" \
    -d '{"input": {"prompt": "你的问题"}}' \
    -o plan.md
    """
    try:
        user_message = request.input.get("prompt", "")
        if not user_message:
            raise HTTPException(
                status_code=400,
                detail="No prompt found in input. Please provide a 'prompt' key in the input.",
            )

        result = attendee_guide_agent.process_message(user_message)
        
        # 格式化为 Markdown
        markdown_content = format_response_to_markdown(result, user_message)
        
        return markdown_content

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Agent processing failed: {str(e)}"
        )


def format_response_to_markdown(result: dict, prompt: str) -> str:
    """将 Agent 响应格式化为 Markdown"""
    
    md_content = f"""# re:Invent 参会规划

**生成时间**: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}

## 您的问题

{prompt}

---

## 规划建议

"""
    
    # 提取消息内容
    messages = result.get("messages", [])
    
    if messages:
        for msg in messages:
            content = msg.get("content", "")
            agent = msg.get("agent", "Unknown")
            chat_type = msg.get("chat_type", "0")
            
            md_content += f"{content}\n\n"
            
            # 添加 agent 信息
            if agent:
                md_content += f"*由 {agent} 提供*\n\n"
    else:
        md_content += "未获取到响应内容\n\n"
    
    md_content += "\n---\n\n"
    md_content += f"*本规划由 re:Invent 参会指南 AI Agent 自动生成*\n"
    
    return md_content


@app.get("/")
async def root():
    return {
        "service": "re:Invent Attendee Guide Agent",
        "version": "1.0.0",
        "endpoints": {
            "health": "/ping",
            "invoke_json": "POST /invocations",
            "invoke_markdown": "POST /invocations/markdown"
        }
    }


@app.get("/ping")
async def ping():
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8081)
