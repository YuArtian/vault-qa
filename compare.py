"""检索方案对比：账本（docs/检索翻车案例.md）里的问题，关键词 vs 向量肩并肩。

用法：
    uv run compare.py
"""

import os

from dotenv import load_dotenv

from retrieval import VectorIndex, pick_notes_vector
from vault import load_notes, pick_notes

load_dotenv()

VAULT_DIR = os.path.expanduser(
    os.environ.get("VAULT_DIR", "~/Documents/Obsidian Vault/Marauder'sMap/Library")
)

QUESTIONS = [
    # 账本案例
    "js的装饰器是什么？",
    "py中有哪些类型",
    # 同义鸿沟：字面零重叠，考验语义理解
    "怎么让程序同时干几件事",
    "程序退出时怎么优雅地清理资源",
    # 关键词时代的成功案例，防止新方案顾此失彼（回归测试思维）
    "conda 多个环境会不会重复占磁盘",
    "os.environ 为什么没有 set 方法",
]


def main() -> None:
    notes = load_notes(VAULT_DIR)
    index = VectorIndex(notes)
    for q in QUESTIONS:
        kw = list(pick_notes(q, notes))
        vec = list(pick_notes_vector(index, q))
        print(f"\n问：{q}")
        print(f"  关键词 → {'、'.join(kw[:5]) or '（空）'}")
        print(f"  向量   → {'、'.join(vec[:5]) or '（空）'}")


if __name__ == "__main__":
    main()
