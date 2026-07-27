# vault-qa

读我 Obsidian 知识库的问答助手——我的第一个 Python 项目，也是学习载体。

## 跑起来

```bash
uv run main.py
```

默认走 Claude 后端（复用本机 Claude Code 登录，不需要 API key）。
想换 OpenAI 兼容服务商：`cp .env.example .env`，填好后设 `LLM_PROVIDER=openai`。

## 文件与它们教的东西

| 文件 | 干什么 | 学到的概念 |
|------|--------|-----------|
| `vault.py` | 读全部笔记 + 关键词计分挑出相关的几篇 | `pathlib.rglob`、dict、推导式、IDF 权重思想、上下文预算 |
| `llm.py` | LLM 后端适配层（claude / openai 双后端） | async generator、`yield`、多 Provider 适配器模式、模块顶层代码的 import 陷阱 |
| `main.py` | 问答循环：挑笔记 → 拼 Prompt → 流式输出 | `asyncio.run`、`async for`、f-string、`os.environ` + dotenv、System Prompt 设计 |

## 踩过的坑（真实记录）

1. **中文关键词切不出来**：`split()` 对中文无效，「装饰器」混在句子里挑错笔记 → 两字滑窗解决
2. **常见词霸榜**：「Python」几乎每篇笔记都有，满篇 Python 的笔记总分最高 → IDF 权重（越常见的词越不值钱）解决——这就是检索的核心直觉，v3 的向量检索是它的高级版
3. **模块顶层读环境变量**：`llm.py` 顶层读 `LLM_PROVIDER`，但 import 发生在 `load_dotenv()` 之前，`.env` 不生效 → 挪到函数内读

## 升级路径（对应《AI开发学习计划》第 0.3 节）

- [x] v1 关键词挑笔记 + 塞 Prompt 问答（LLM 应用基础）
- [ ] v2 答案带结构化出处（Pydantic + Structured Output）
- [ ] v3 笔记多了挑不准 → 向量检索（Embedding + pgvector）
- [ ] v4 做成 FastAPI 接口，手机上能问（Web 服务开发）
- [ ] v5 评估答得准不准（LLM-as-Judge + golden set）
- [ ] v6 让它自己决定翻哪篇笔记（Tool Calling + Agent）

## 自己动手的练习

1. 给 `pick_notes` 加一个参数控制返回篇数上限，体会默认参数写法
2. 把 `[参考笔记]` 打印改成显示每篇的得分（改 `pick_notes` 返回值试试 tuple）
3. 问答循环里输入 `!notes` 时列出所有笔记名——练 dict 遍历和字符串判断
4. 故意把 `.env` 里 `LLM_PROVIDER` 设成 openai 但不填 key，看 `KeyError` 长什么样，再想想为什么「启动即崩」是好设计
