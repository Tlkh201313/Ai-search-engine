"""
OpenAI-compatible and Anthropic-compatible tool definitions.
Pass TOOLS to any AI model that supports function/tool calling.
Works with Ollama, LM Studio, vLLM, llama.cpp, OpenAI API, Anthropic.
"""

OPENAI_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Search the web. Auto-rotates across 6+ backends with no rate limits.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query to look up.",
                    },
                    "max_results": {
                        "type": "integer",
                        "default": 5,
                        "description": "Number of results to return (1-20).",
                    },
                    "backend": {
                        "type": "string",
                        "enum": [
                            "duckduckgo",
                            "brave",
                            "bing_scrape",
                            "mojeek",
                            "searxng",
                            "wiby",
                        ],
                        "description": "Force a specific backend. If omitted, auto-rotates.",
                    },
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_all_backends",
            "description": "Query ALL backends simultaneously and merge deduplicated results.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query to look up.",
                    },
                    "max_results": {
                        "type": "integer",
                        "default": 3,
                        "description": "Max results per backend (1-10).",
                    },
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "fetch_page",
            "description": "Fetch a web page and return clean readable text.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "The URL to fetch."},
                    "max_chars": {
                        "type": "integer",
                        "default": 8000,
                        "description": "Maximum characters to return (500-50000).",
                    },
                    "js_render": {
                        "type": "boolean",
                        "default": False,
                        "description": "Use Playwright for JS-heavy pages.",
                    },
                },
                "required": ["url"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "scrape_page",
            "description": "Scrape a page for structured data: headings, links, paragraphs, meta tags.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "The URL to scrape."}
                },
                "required": ["url"],
            },
        },
    },
]

ANTHROPIC_TOOLS = [
    {
        "name": "web_search",
        "description": "Search the web. Auto-rotates across 6+ backends with no rate limits.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query to look up.",
                },
                "max_results": {
                    "type": "integer",
                    "default": 5,
                    "description": "Number of results to return (1-20).",
                },
                "backend": {
                    "type": "string",
                    "enum": [
                        "duckduckgo",
                        "brave",
                        "bing_scrape",
                        "mojeek",
                        "searxng",
                        "wiby",
                    ],
                    "description": "Force a specific backend. If omitted, auto-rotates.",
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "search_all_backends",
        "description": "Query ALL backends simultaneously and merge deduplicated results.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query to look up.",
                },
                "max_results": {
                    "type": "integer",
                    "default": 3,
                    "description": "Max results per backend (1-10).",
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "fetch_page",
        "description": "Fetch a web page and return clean readable text.",
        "input_schema": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "The URL to fetch."},
                "max_chars": {
                    "type": "integer",
                    "default": 8000,
                    "description": "Maximum characters to return (500-50000).",
                },
                "js_render": {
                    "type": "boolean",
                    "default": False,
                    "description": "Use Playwright for JS-heavy pages.",
                },
            },
            "required": ["url"],
        },
    },
    {
        "name": "scrape_page",
        "description": "Scrape a page for structured data: headings, links, paragraphs, meta tags.",
        "input_schema": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "The URL to scrape."}
            },
            "required": ["url"],
        },
    },
]

TOOLS = OPENAI_TOOLS

TOOL_CONFIG = {
    "parallel_tool_calls": True,
    "tool_choice": "auto",
}
