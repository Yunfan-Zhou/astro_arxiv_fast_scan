# arXiv Daily Reader

说一句“帮我抓今天的文献”，从 [Giiisp 的 Astrophysics 页面](https://www.giiisp.com/#/arxiv?subjectId=1399191569822654465&arxivFilterTimelineSelected=1) 抓取完整最新列表，交给 dots/Sol 子 agent 分批速读，得到一份中文 Markdown。感兴趣就收藏，后续再精读。暂不建设知识库。

## 用法

Python 3.11+，基础流程仅标准库，不需要额外模型 key。先让 dots 读取 [技能](skills/arxiv-daily-reader/SKILL.md)，或按 [dots 入口说明](docs/DOTS.md) 接续。

```bash
# 在仓库根目录；如有指定 myenv，用该环境的 Python 绝对路径。
python -m arxiv_daily
python -m arxiv_daily.prepare
# 让阅读 agent 按 work/ 中批次指令写 readings/YYYY-MM-DD/read_*.json
python -m arxiv_daily.assemble --readings readings/YYYY-MM-DD
# 收藏用 arXiv ID；“第N篇”由 dots 从当前日报定位
python -m arxiv_daily.library 2610.00062 --note '后续精读'
python -m unittest discover -s tests -v
```

默认按北京时间当天查询，覆盖三类列表；`--sections 1 2` 可排除修订稿，`--date YYYY-MM-DD` 可指定日期，`--subject` 与 `--level` 可更换学科。

抓取前后核验来源“更新完毕”，分页直到空页，并要求两轮内容一致。未就绪返回 3，失败返回 1，不发布不完整列表。`data/latest.json` 是最新成功查询指针，消费者必须检查日期。无数据日期仍以网站响应为准。来源学科 ID、接口行为与限制见 [SOURCE.md](docs/SOURCE.md)。

## 输出

| 文件 | 用途 |
|---|---|
| `data/latest.json` | 日期、状态、批次路径 |
| `data/日期/哈希/papers.json` | 标题、作者原文、摘要、来源关键词及版本链接 |
| `work/哈希/batch-*.txt` | 紧凑阅读批次，避免每篇重复长提示词 |
| `reports/日期/daily.md` | 单个 Markdown 日报，带可编辑收藏复选框 |
| `reports/日期/reader.html` | 可选离线页面：搜索、点星标、导出收藏 |
| `library/favorites.json` | dots 命令收藏清单，默认不提交 |

抓取器不会独自生成中文解读，也不连接未知的 dots API。`tasks.jsonl` 保留逐篇兼容入口，但节约 token 时应使用紧凑批次。按需执行是默认模式，GitHub Actions 仅提供手动抓取，不会擅自每天调用模型。

收藏页使用浏览器本地存储，**不跨设备自动同步**，请导出 JSON/Markdown 备份。文件模式下部分浏览器会限制存储，页面会提示；也可 `python -m http.server 8765 --bind 127.0.0.1` 后访问本地页面。Markdown 本身不提供跨应用的持久化点击按钮。

## 少量关键图表

可选依赖 `python -m pip install '.[figures]'`。按 [FIGURES.md](docs/FIGURES.md) 扫描图注候选，选择并渲染原 PDF 关键页面，每篇最多2张图/表；必须实际视觉验收后才能附入报告。不会对124篇自动读全部图，也不会把仅看摘要称作图表核验。

接口是网站前端所用公开接口，可能变化；失败会明确报错。关键词缺失保持“来源未提供”，不伪造作者关键词。源站日期不同于 arXiv 首次提交日期。论文摘要与元数据归原作者/来源所有；本项目代码不改变其权利。
