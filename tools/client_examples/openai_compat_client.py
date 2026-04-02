"""
OpenAI-compatible client.
LM Studio: base_url = "http://localhost:1234/v1"
vLLM:      base_url = "http://localhost:8001/v1"
llama.cpp: base_url = "http://localhost:8080/v1"
"""
from openai import AsyncOpenAI
import httpx, json, asyncio
from tools.tool_definitions import TOOLS

SERVER = "http://localhost:8000"

async def execute_tool(name: str, args: dict) -> str:
    async with httpx.AsyncClient() as c:
        if name == "web_search":
            r = await c.get(f"{SERVER}/search", params={"q": args["query"], "max_results": args.get("max_results",5)}, timeout=15)
        elif name == "fetch_page":
            r = await c.get(f"{SERVER}/fetch", params={"url": args["url"]}, timeout=20)
        elif name == "scrape_page":
            r = await c.get(f"{SERVER}/scrape", params={"url": args["url"]}, timeout=20)
        else:
            return json.dumps({"error": f"Unknown tool: {name}"})
    return json.dumps(r.json(), indent=2)

async def chat(user_message: str, base_url: str = "http://localhost:1234/v1", model: str = "qwen2.5"):
    ai = AsyncOpenAI(base_url=base_url, api_key="not-needed")
    messages = [{"role": "user", "content": user_message}]
    while True:
        resp = await ai.chat.completions.create(model=model, messages=messages, tools=TOOLS, tool_choice="auto")
        choice = resp.choices[0]; msg = choice.message
        messages.append(msg.model_dump())
        if choice.finish_reason != "tool_calls" or not msg.tool_calls:
            print(msg.content); return msg.content
        for call in msg.tool_calls:
            result = await execute_tool(call.function.name, json.loads(call.function.arguments))
            messages.append({"role": "tool", "tool_call_id": call.id, "content": result})

if __name__ == "__main__":
    asyncio.run(chat("Summarise top news today"))
