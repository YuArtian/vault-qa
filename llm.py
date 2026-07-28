"""LLM 后端适配层——「多 Provider 适配器」模式的最小版本。

两个后端，用环境变量 LLM_PROVIDER 切换：
- claude（默认）：走 Claude Agent SDK，复用本机 Claude Code 的登录，不需要 API key
- openai：任何 OpenAI 兼容服务商（OpenAI / DeepSeek / OpenRouter...），需要 .env 配 key

v2 变化：流式的 stream_answer 换成了一次性返回的 complete——
结构化输出要拿到完整 JSON 才能校验，和逐字流式天然矛盾（这个取舍 v4 再回头解决）。
v1 的流式实现永远留在 git tag v1 里。
"""

import os


async def complete(system_prompt: str, question: str) -> str:
    """调一次 LLM，返回完整回答文本。"""
    # 在函数里读环境变量，而不是模块顶层——顶层代码在 import 瞬间就执行，那时 load_dotenv() 还没跑
    if os.environ.get("LLM_PROVIDER", "claude") == "claude":
        from claude_agent_sdk import AssistantMessage, ClaudeAgentOptions, TextBlock, query

        options = ClaudeAgentOptions(
            system_prompt=system_prompt,
            max_turns=1,        # 只要一问一答，不让它自主多轮
            allowed_tools=[],   # 纯问答，不给任何工具
        )
        parts: list[str] = []
        async for message in query(prompt=question, options=options):
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, TextBlock):
                        parts.append(block.text)
        return "".join(parts)

    from openai import AsyncOpenAI

    client = AsyncOpenAI(
        api_key=os.environ["LLM_API_KEY"],
        base_url=os.environ.get("LLM_BASE_URL"),
    )
    resp = await client.chat.completions.create(
        model=os.environ.get("LLM_MODEL", "gpt-4o-mini"),
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": question},
        ],
    )
    return resp.choices[0].message.content or ""
