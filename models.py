"""回答的数据模型——v2 的核心：出处从「Prompt 口头约定」升级为「schema 保证」。

对照 Zod：
    const Answer = z.object({
      answer: z.string(),
      sources: z.array(z.string()).default([]),
    })
"""

from pydantic import BaseModel, Field


class Answer(BaseModel):
    """LLM 必须按这个形状回答。字段的 description 会进 JSON Schema，模型看得到。"""

    answer: str = Field(description="对问题的中文回答；笔记里没写就直说没写，禁止编造")
    sources: list[str] = Field(
        default_factory=list,
        description="答案依据的笔记名列表，只能填提供的笔记里出现过的名字；没有依据时为空列表",
    )
