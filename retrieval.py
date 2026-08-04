"""向量检索（v3）：Embedding 模型把「意思」编码成高维空间的位置，语义相近 = 几何距离近。

对比 v1/v2 的关键词方案（vault.py 的 pick_notes，保留作 baseline）：
- 关键词：数「字」出现次数——同义改写就瞎、分词靠猜、字面命中但语义跑偏
- 向量：模型读整句话的意思——「同时干几件事」和「并发编程」字面零重叠，向量却几乎同向

本地跑 BAAI/bge-small-zh-v1.5（约 100MB，中文效果好），不需要任何 API key。
"""

import hashlib
import re
from pathlib import Path

import numpy as np

MODEL_NAME = "BAAI/bge-small-zh-v1.5"
# bge 官方建议：查询侧加这个前缀，文档侧不加——问题和文档在模型眼里是两种角色
QUERY_PREFIX = "为这个句子生成表示以用于检索相关文章："
CACHE_FILE = Path(__file__).parent / ".embedding_cache.npz"

CHUNK_SIZE = 380   # bge 一次最多读约 512 token（中文约一字一 token），超长会被静默截断
CHUNK_OVERLAP = 40  # 相邻块重叠一点，防止一句话被拦腰切断后两边都查不到


def split_chunks(notes: dict[str, str]) -> list[dict]:
    """把笔记切成带出处的小块：先按 ## 标题切（顺着作者的结构），过长的再硬切。"""
    chunks = []
    for name, text in notes.items():
        for section in re.split(r"\n(?=## )", text):
            section = section.strip()
            if not section:
                continue
            for piece in _wrap(section):
                chunks.append({"note": name, "text": piece})
    return chunks


def _wrap(text: str) -> list[str]:
    if len(text) <= CHUNK_SIZE:
        return [text]
    pieces, i = [], 0
    while i < len(text):
        pieces.append(text[i : i + CHUNK_SIZE])
        i += CHUNK_SIZE - CHUNK_OVERLAP
    return pieces


class VectorIndex:
    """构建时把全部块编码成向量矩阵；查询时算一次余弦相似度取最近的块。"""

    def __init__(self, notes: dict[str, str]):
        # 重量级 import 放这里：加载 torch 要几秒，别拖累不用向量检索的场景
        from sentence_transformers import SentenceTransformer

        self.model = SentenceTransformer(MODEL_NAME)
        self.chunks = split_chunks(notes)
        self.vectors = self._embed_all()

    def _embed_all(self) -> np.ndarray:
        """全量编码，带磁盘缓存：内容没变的块直接复用上次的向量（Embedding 缓存）。"""
        texts = [f"{c['note']}\n{c['text']}" for c in self.chunks]  # 块前面拼上笔记名，检索更准
        keys = [hashlib.md5(t.encode()).hexdigest() for t in texts]

        cached: dict[str, np.ndarray] = {}
        if CACHE_FILE.exists():
            data = np.load(CACHE_FILE)
            cached = dict(zip(data["keys"], data["vecs"]))

        missing = [i for i, k in enumerate(keys) if k not in cached]
        if missing:
            print(f"（编码 {len(missing)}/{len(texts)} 个新块…）")
            new_vecs = self.model.encode(
                [texts[i] for i in missing],
                normalize_embeddings=True,  # 归一化后，点积 = 余弦相似度
                show_progress_bar=len(missing) > 50,
            )
            for i, vec in zip(missing, new_vecs):
                cached[keys[i]] = vec
            np.savez(
                CACHE_FILE,
                keys=np.array(list(cached.keys())),
                vecs=np.array(list(cached.values())),
            )
        return np.array([cached[k] for k in keys])

    def search(self, question: str, k: int = 12) -> list[tuple[dict, float]]:
        q = self.model.encode([QUERY_PREFIX + question], normalize_embeddings=True)[0]
        scores = self.vectors @ q  # 一次矩阵乘法算完和所有块的相似度
        top = np.argsort(scores)[::-1][:k]
        return [(self.chunks[i], float(scores[i])) for i in top]


MIN_SCORE = 0.4  # 相似度低于这个就当无关，宁可空手也不硬凑


def pick_notes_vector(index: VectorIndex, question: str, limit_chars: int = 24000) -> dict[str, str]:
    """返回和 vault.pick_notes 相同的形状 {笔记名: 内容}，可直接替换。

    区别：内容不再是整篇笔记，而是真正相关的那几块——同样的预算装下更高的信息密度。
    """
    picked: dict[str, list[str]] = {}
    used = 0
    for chunk, score in index.search(question):
        if score < MIN_SCORE:
            break
        if used + len(chunk["text"]) > limit_chars:
            continue
        picked.setdefault(chunk["note"], []).append(chunk["text"])
        used += len(chunk["text"])
    return {name: "\n……\n".join(pieces) for name, pieces in picked.items()}
