"""知识库问答助手 v1：挑出相关笔记塞进 Prompt，让 LLM 带出处回答。

用法：
    uv run main.py        # 进入问答循环，输入 q 退出
"""

import asyncio
import os

from dotenv import load_dotenv

from llm import stream_answer
from vault import load_notes, pick_notes

load_dotenv()  # 把 .env 加载进 os.environ（见笔记《0.02 环境变量与配置》）

VAULT_DIR = os.path.expanduser(
    os.environ.get("VAULT_DIR", "~/Documents/Obsidian Vault/Marauder'sMap/Library")
)

SYSTEM_PROMPT = """你是我的私人知识库助手。只根据下面提供的笔记内容回答问题。

规则：
1. 回答末尾用「出处：《笔记名》」标注答案来自哪几篇笔记
2. 笔记里没写的内容，直接说「笔记里没写」，禁止编造
3. 用中文回答，简洁清楚

以下是笔记内容：

{context}"""


async def ask(question: str, notes: dict[str, str]) -> None:
    picked = pick_notes(question, notes)
    if not picked:
        print("没找到相关笔记，换个问法试试？\n")
        return
    print(f"[参考笔记] {'、'.join(picked)}\n")

    context = "\n\n".join(f"# 《{name}》\n{text}" for name, text in picked.items())
    system_prompt = SYSTEM_PROMPT.format(context=context)
    async for piece in stream_answer(system_prompt, question):
        print(piece, end="", flush=True)
    print("\n")


async def main() -> None:
    notes = load_notes(VAULT_DIR)
    print(f"已加载 {len(notes)} 篇笔记 ← {VAULT_DIR}")
    print("输入问题开始提问，q 退出\n")
    while True:
        try:
            question = input("你问：").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if question in ("q", "quit", "exit"):
            break
        if question:
            await ask(question, notes)


if __name__ == "__main__":
    asyncio.run(main())  # JS 的事件循环是内建的，Python 要显式启动——就是这一行
