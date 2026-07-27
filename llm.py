"""LLM 后端适配层——大纲里「多 Provider 适配器」模式的最小版本。

两个后端，用环境变量 LLM_PROVIDER 切换：
- claude（默认）：走 Claude Agent SDK，复用本机 Claude Code 的登录，不需要 API key
- openai：任何 OpenAI 兼容服务商（OpenAI / DeepSeek / OpenRouter...），需要 .env 配 key

对照 JS：AsyncIterator[str] ≈ AsyncGenerator<string>，async for ≈ for await...of
"""

import os
from collections.abc import AsyncIterator

async def stream_answer(system_prompt: str, question: str) -> AsyncIterator[str]:
    """把回答一段一段地 yield 出来，调用方 async for 消费。"""
    # 注意：在函数里读环境变量，而不是模块顶层——
    # 顶层代码在 import 瞬间就执行，那时 load_dotenv() 还没跑
    if os.environ.get("LLM_PROVIDER", "claude") == "claude":
        from claude_agent_sdk import AssistantMessage, ClaudeAgentOptions, TextBlock, query

        options = ClaudeAgentOptions(
            system_prompt=system_prompt,
            max_turns=1,        # 只要一问一答，不让它自主多轮
            allowed_tools=[],   # 纯问答，不给任何工具
        )
        async for message in query(prompt=question, options=options):
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, TextBlock):
                        yield block.text
    else:
        from openai import AsyncOpenAI

        client = AsyncOpenAI(
            api_key=os.environ["LLM_API_KEY"],
            base_url=os.environ.get("LLM_BASE_URL"),
        )
        stream = await client.chat.completions.create(
            model=os.environ.get("LLM_MODEL", "gpt-4o-mini"),
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": question},
            ],
            stream=True,  # 真·逐 token 流式
        )
        async for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
