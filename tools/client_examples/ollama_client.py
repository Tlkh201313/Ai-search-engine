"""Connect Qwen/LLaMA/Mistral via Ollama.
Supports parallel tool calls and streaming responses.
"""

import ollama
import httpx
import json
import asyncio
from tools.tool_definitions import TOOLS, TOOL_CONFIG

SERVER = "http://localhost:8000"


async def execute_tool(name: str, args: dict) -> str:
    async with httpx.AsyncClient() as c:
        if name == "web_search":
            r = await c.get(
                f"{SERVER}/search",
                params={"q": args["query"], "max_results": args.get("max_results", 5)},
                timeout=15,
            )
        elif name == "search_all_backends":
            r = await c.get(
                f"{SERVER}/search/all", params={"q": args["query"]}, timeout=20
            )
        elif name == "fetch_page":
            r = await c.get(
                f"{SERVER}/fetch",
                params={"url": args["url"], "js_render": args.get("js_render", False)},
                timeout=20,
            )
        elif name == "scrape_page":
            r = await c.get(f"{SERVER}/scrape", params={"url": args["url"]}, timeout=20)
        else:
            return json.dumps({"error": f"Unknown tool: {name}"})
    return json.dumps(r.json(), indent=2)


async def chat(user_message: str, model: str = "qwen2.5"):
    messages = [{"role": "user", "content": user_message}]
    while True:
        resp = ollama.chat(
            model=model,
            messages=messages,
            tools=TOOLS,
            stream=False,
        )
        msg = resp.message
        messages.append(
            {
                "role": "assistant",
                "content": msg.content or "",
                "tool_calls": msg.tool_calls,
            }
        )
        if not msg.tool_calls:
            print(msg.content)
            return msg.content
        tool_calls = (
            msg.tool_calls if isinstance(msg.tool_calls, list) else [msg.tool_calls]
        )
        tasks = []
        for call in tool_calls:
            args = call.function.arguments
            if isinstance(args, str):
                args = json.loads(args)
            tasks.append(execute_tool(call.function.name, args))
        results = await asyncio.gather(*tasks)
        for result in results:
            messages.append({"role": "tool", "content": result})


if __name__ == "__main__":
    asyncio.run(chat("What happened in AI today?"))
