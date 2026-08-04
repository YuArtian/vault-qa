"""知识库问答助手 v3：向量检索——按语义而不是字面挑笔记。

用法：
    uv run main.py                    # 默认向量检索（首次启动会下载模型并编码笔记）
    RETRIEVER=keyword uv run main.py  # 切回 v1 的关键词检索（对比用 baseline）
"""

import asyncio
import json
import os
import re

from dotenv import load_dotenv
from pydantic import ValidationError

from llm import complete
from models import Answer
from vault import load_notes, pick_notes

load_dotenv()

VAULT_DIR = os.path.expanduser(
    os.environ.get("VAULT_DIR", "~/Documents/Obsidian Vault/Marauder'sMap/Library")
)

SYSTEM_PROMPT = """你是我的私人知识库助手。只根据下面提供的笔记内容回答问题。

你必须只输出一个 JSON 对象——不要 markdown 代码块，不要任何多余文字——符合这个 JSON Schema：
{schema}

要求：
1. sources 只能填下面笔记内容里出现过的笔记名；答案没有依据时留空列表
2. 笔记里没写的内容，在 answer 里直说「笔记里没写」，禁止编造
3. answer 用中文，简洁清楚

以下是笔记内容：

{context}"""

MAX_RETRIES = 3


def strip_fences(text: str) -> str:
    """模型经常不听话地包一层 ```json 代码块，先剥掉再解析。"""
    return re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip())


async def ask(question: str, retrieve) -> None:
    picked = retrieve(question)
    if not picked:
        print("没找到相关笔记，换个问法试试？\n")
        return
    print(f"[参考笔记] {'、'.join(picked)}")

    context = "\n\n".join(f"# 《{name}》\n{text}" for name, text in picked.items())
    schema = json.dumps(Answer.model_json_schema(), ensure_ascii=False)  # ensure_ascii=False：让中文 description 原样进 Prompt
    system_prompt = SYSTEM_PROMPT.format(schema=schema, context=context)

    prompt = question
    for attempt in range(1, MAX_RETRIES + 1):
        print(f"（思考中，第 {attempt} 次）", flush=True)
        raw = await complete(system_prompt, prompt)

        # 第一层验收：形状对不对（schema 校验，不对会抛 ValidationError）
        try:
            answer = Answer.model_validate_json(strip_fences(raw))
        except ValidationError as e:
            prompt = (
                f"{question}\n\n"
                f"你上一次的输出不是合法的 JSON 或不符合 Schema，校验错误如下：\n{e}\n"
                f"请修正后重新输出，只输出 JSON 对象本身。"
            )
            continue

        # 第二层验收：出处是不是真的存在（业务规则校验，防「幻觉出处」）
        fake_sources = [s for s in answer.sources if s not in picked]
        if fake_sources:
            prompt = (
                f"{question}\n\n"
                f"你上一次填的出处 {fake_sources} 并不在提供的笔记里。"
                f"sources 只能从这些笔记名里选：{list(picked)}。请重新输出 JSON。"
            )
            continue

        print(f"\n{answer.answer}")
        if answer.sources:
            print("\n出处：" + "、".join(f"《{s}》" for s in answer.sources))
        print()
        return

    print(f"重试 {MAX_RETRIES} 次都没拿到合格的回答，这题先跳过。\n")


def build_retriever(notes: dict[str, str]):
    """返回一个「问题 → {笔记名: 内容}」的函数。检索策略在这里切换，ask 不感知差异。"""
    if os.environ.get("RETRIEVER", "vector") == "keyword":
        print("[检索] 关键词（v1 baseline）")
        return lambda q: pick_notes(q, notes)

    from retrieval import VectorIndex, pick_notes_vector  # 重依赖，用到才 import

    print("[检索] 向量（bge-small-zh，本地推理）")
    index = VectorIndex(notes)
    return lambda q: pick_notes_vector(index, q)


async def main() -> None:
    notes = load_notes(VAULT_DIR)
    print(f"已加载 {len(notes)} 篇笔记 ← {VAULT_DIR}")
    retrieve = build_retriever(notes)
    print("输入问题开始提问，q 退出\n")
    while True:
        try:
            question = input("你问：").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if question in ("q", "quit", "exit"):
            break
        if question:
            await ask(question, retrieve)


if __name__ == "__main__":
    asyncio.run(main())
