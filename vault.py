"""读取 Obsidian 笔记 + 用最笨的关键词计数挑出相关的几篇。

v1 的挑选方法故意很笨（数关键词出现次数）——
等你发现它挑不准的那天，就是该学 RAG（语义检索）的那天。
"""

import math
import re
from pathlib import Path


def load_notes(vault_dir: str) -> dict[str, str]:
    """把目录下所有 .md 读进内存，返回 {笔记名: 全文}。

    对照 JS：Path.rglob("*.md") ≈ glob("**/*.md")
    """
    notes = {}
    for path in Path(vault_dir).rglob("*.md"):
        notes[path.stem] = path.read_text(encoding="utf-8")
    return notes


def pick_notes(question: str, notes: dict[str, str], limit_chars: int = 24000) -> dict[str, str]:
    """按「问题里的词在笔记里出现的次数」打分，取最相关的几篇，塞满预算为止。

    limit_chars 就是 v1 的「上下文窗口」意识：不能把整个知识库塞给模型。
    """
    # 英文按单词切；中文没有空格分词，用两字滑窗：「装饰器是什么」→ 装饰/饰器/器是/是什/什么
    ascii_words = re.findall(r"[A-Za-z][A-Za-z0-9_.+-]+", question)
    cjk_runs = re.findall(r"[一-鿿]{2,}", question)
    words = ascii_words + [run[i : i + 2] for run in cjk_runs for i in range(len(run) - 1)]

    # IDF 权重：一个词出现在越多笔记里越没有区分度——
    # 「Python」几乎每篇都有，不该加分；「装饰」只在几篇出现，才是真信号
    total = len(notes)
    idf = {}
    for w in set(words):
        df = sum(1 for text in notes.values() if w in text)  # 多少篇笔记包含这个词
        idf[w] = math.log((total + 1) / (df + 1)) + 0.1

    scored = []
    for name, text in notes.items():
        score = sum(
            (min(text.count(w), 8) + (w in name) * 5) * idf[w]  # 次数封顶防刷分；标题命中 5 倍
            for w in set(words)
        )
        if score > 0:
            scored.append((score, name))
    scored.sort(reverse=True)

    picked: dict[str, str] = {}
    used = 0
    for _score, name in scored:
        if used + len(notes[name]) > limit_chars:
            continue
        picked[name] = notes[name]
        used += len(notes[name])
    return picked
