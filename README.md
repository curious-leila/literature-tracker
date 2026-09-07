# LLM 内容甄选与智能推送工作流

面向知网 / WOS 跨平台文献筛选，完成“人工导出 → 自动解析去重 → LLM 语义分层 → 简报生成 → 邮件推送”的可解释工作流。

[在线证据页](https://curious-leila.github.io/literature-tracker/) · [运行证据 JSON](https://curious-leila.github.io/literature-tracker/run-summary.json) · [Prompt 迭代记录](docs/prompt-tuning-log.md)

## 为什么做

项目源于“翻译学 × 文化记忆”小众交叉选题。知网与 WOS 的结果分散在不同格式中，跨关键词、跨周检索还会反复出现同一篇文献；需求阶段估算每周约需 2 小时逐篇判断。该时长是自述基线，未做受控计时实验。

系统明确保留人工边界：用户负责在有权限的平台检索并导出文件；从文件导入开始，解析、历史去重、LLM 分类、结果整理和邮件交付自动完成。

## 一次真实运行

以下数字由 [`scripts/build_evidence.py`](scripts/build_evidence.py) 从 5 份真实导出文件与脱敏运行快照交叉计算，不是前端手填数据。

| 口径 | 结果 |
|---|---:|
| 导出文件 | 5 份 |
| 解析记录 | 161 条 |
| 去重后唯一文献 | 159 篇 |
| 分类分布 | 高 12 / 中 61 / 低 86 |
| 保留原文入口 | 156 / 159 篇 |
| 结构化结果解析 | 159 / 159 条 |

“159 / 159”只表示结果成功解析并进入下游，不等于分类准确率。当前没有人工金标集，因此不声称 85% 准确率；也没有保留计时实验，因此不声称“2 小时缩短至 5 分钟”。

## 产品与工程设计

```text
人工：知网 / WOS 检索与导出
                  ↓ 自动化边界
双格式解析 → SQLite 历史去重 → Qwen 三级筛选 → 简报生成 → SMTP 推送
```

- `parser.py`：解析 CNKI RefWorks 与 WOS RIS，统一字段并生成标题指纹。
- `pipeline.py`：编排收集、分析、格式化和交付；分析不完整时拒绝整批写入，邮件失败时保留未推送状态供重试。
- `data/recorded-run.json`：不含密钥的真实运行快照，供公开复算。
- `web/`：Vite + React + TypeScript 证据页，只消费生成后的 `run-summary.json`。

## 一键核验证据

```bash
pip install -r requirements.txt
python -m unittest discover -s tests -v
python scripts/build_evidence.py --check
```

重新生成公开 JSON：

```bash
python scripts/build_evidence.py
```

只有维护者需要从本地 SQLite 刷新公开快照：

```bash
python scripts/build_evidence.py --capture-snapshot
```

## 本地预览证据页

```bash
cd web
npm ci
npm run dev
```

生产构建使用 `npm run build`，GitHub Actions 将 `web/dist/` 发布到 GitHub Pages。

## 项目边界

- 数据源仍需人工导出，原因是知网 / WOS 的学校权限与检索策略不能由公开工作流接管。
- 分类准确率尚未通过独立人工金标评测。
- 输入、判断与输出层已形成迁移方案，但竞品情报、用户反馈等跨领域场景尚未实测。

