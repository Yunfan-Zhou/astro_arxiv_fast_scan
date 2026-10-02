# arXiv Daily Reader

说一句“帮我抓今天的文献”，从 [Giiisp 的 Astrophysics 页面](https://www.giiisp.com/#/arxiv?subjectId=1399191569822654465&arxivFilterTimelineSelected=1) 抓取完整最新列表，保留星系（astro-ph.GA）和宇宙学（astro-ph.CO）分类，交给 dots/Sol 子 agent 分批速读，阅读摘要和每篇1–2张关键图，得到一份中文 Markdown。感兴趣就收藏，后续再精读。收藏与精读列表持续积累为个人文献库。

## 用法

在 Codex 安装一次，即可自然语言触发：

```bash
git clone https://github.com/Yunfan-Zhou/astro_arxiv_fast_scan.git
cd astro_arxiv_fast_scan
python scripts/install_skill.py
```

默认安装到 `$CODEX_HOME/skills/arxiv-daily-reader`（未设置时为 `~/.codex/skills/arxiv-daily-reader`），附带完整运行代码；输出保存在 `~/astro_arxiv_fast_scan_output/`。`--workspace` 可指定输出目录，`--destination` 可指定其他技能目录。已有同名技能时安装器停止，避免覆盖。

新开一个 Codex 聊天，说 **“我想进行当天最新的 arxiv 论文速览”**。技能已启用自然语言自动选择，也可显式输入 `$arxiv-daily-reader`。如果未出现在技能列表，重新加载技能或重启客户端。

**ChatGPT dots 云端调用**：让 dot 从本仓库克隆代码、读取 `skills/arxiv-daily-reader/SKILL.md`，并固定使用同一个云端输出目录。无需连接 Mac 才能跑这个工作流；本机技能和数据库不会自动同步到云端。可直接复制[给 dots 的首次初始化指令](docs/DOTS.md)。

Python 3.11+，基础流程仅标准库，不需要额外模型 key。先让 dots 读取 [技能](skills/arxiv-daily-reader/SKILL.md)，或按 [dots 入口说明](docs/DOTS.md) 接续。

```bash
# 在仓库根目录；如有指定 myenv，用该环境的 Python 绝对路径。
python -m arxiv_daily
python -m arxiv_daily.prepare
# 让阅读 agent 按 work/ 中批次指令写 readings/YYYY-MM-DD/read_*.json
python -m arxiv_daily.assemble --readings readings/YYYY-MM-DD --require-figures
# 完整编排（含图表队列）建议使用 skills/arxiv-daily-reader/scripts/run.py start / finish
# 按正在看的那份日报编号加入精读库
python -m arxiv_daily.library add --report reports/日期/批次哈希/daily.md --indices 001,002 --list deep-read
python -m unittest discover -s tests -v
```

默认按北京时间当天查询，覆盖三类列表，主分类或交叉分类命中 astro-ph.GA / astro-ph.CO 任一即保留，先筛选再送入模型；`--all-subjects` 显式关闭分类筛选，`--categories` 可指定分类；`--sections 1 2` 可排除修订稿，`--date YYYY-MM-DD` 可指定日期，`--subject` 与 `--level` 可更换学科。

抓取前后核验来源“更新完毕”，分页直到空页，并要求两轮内容一致。未就绪返回 3，失败返回 1，不发布不完整列表。`data/latest.json` 是最新成功查询指针，消费者必须检查日期。无数据日期仍以网站响应为准。来源学科 ID、接口行为与限制见 [SOURCE.md](docs/SOURCE.md)。

## 输出

| 文件 | 用途 |
|---|---|
| `data/latest.json` | 日期、状态、批次路径 |
| `data/日期/哈希/papers.json` | 标题、作者原文、摘要、来源关键词及版本链接 |
| `work/哈希/detailed-v2/batch-*.txt` | 紧凑阅读批次，避免每篇重复长提示词 |
| `reports/日期/批次哈希/daily.md` | 单个 Markdown 日报，带可编辑收藏复选框 |
| `reports/日期/批次哈希/reader.html` | 可选离线页面：搜索、点星标、导出收藏 |
| `reports/日期/批次哈希/paper-index.json` | 该日报编号对应的元数据快照，防止收藏错篇 |
| `library/papers.csv` | Excel 可打开的完整收藏/精读库，每次合并后自动导出 |
| `library/papers.sqlite3` | 持久主库，事务保存、按 arXiv ID 去重 |
| `library/favorites.json` | 兼容旧版的收藏导出，默认不提交 |

抓取器不会独自生成中文解读，也不连接未知的 dots API。`tasks.jsonl` 保留逐篇兼容入口，但节约 token 时应使用紧凑批次。按用户命令执行是默认模式，GitHub Actions 仅提供手动抓取，不会擅自每天调用模型。

收藏页使用浏览器本地存储，**不跨设备自动同步**，请导出 JSON/Markdown 备份。文件模式下部分浏览器会限制存储，页面会提示；也可 `python -m http.server 8765 --bind 127.0.0.1` 后访问本地页面。Markdown 本身不提供跨应用的持久化点击按钮。

## 阅读详略

默认单篇正文约800–1400汉字，分为研究背景和问题定义、主要方法和创新点、关键结果和贡献、潜在应用和意义四节，并保留元数据表和原始摘要。摘要信息少时允许更短，不补造方法和结论。每批8篇，由 Sol 中推理子 agent 处理；默认每篇附1–2张关键图及逐图讲解；优先核心结果、关键对照和能补充摘要限制的图。

阅读格式版本 `detailed-v2` 隔离旧简版缓存，下次调用不会把旧版四句总结当成详细版。详细版输出 token 会增加；实际消耗应重新测量，不能沿用短版试跑的用量。原始摘要由代码直接附加，不额外调用模型重写。

## 少量关键图表

可选依赖 `python -m pip install '.[figures]'`。按 [FIGURES.md](docs/FIGURES.md) 扫描图注候选，选择并渲染原 PDF 关键页面，每篇最多2张图/表；必须实际视觉验收后才能附入报告。对筛选后的每篇读取关键图，不逐页读全文图片。每张必须解释坐标/单位、主要趋势/比较、误差和与摘要结论的关系；缺讲解或未验收的图不能通过 `finish`。图表状态和失败原因计入报告，旧版纯摘要交付缓存不会当成完整结果。

接口是网站前端所用公开接口，可能变化；失败会明确报错。关键词缺失保持“来源未提供”，不伪造作者关键词。源站日期不同于 arXiv 首次提交日期。论文摘要与元数据归原作者/来源所有；本项目代码不改变其权利。

## 持久收藏与精读队列

对 dots 说“把这份日报的001、002加入精读列表”，它会读取对应报告的固定索引，保存标题、作者、URL、关键词、摘要、分类、版本、时间、备注及阅读状态。不同日期持续写入同一文献库；重复添加合并，新版本不产生重复论文行。收藏与精读为两个独立标记，同一论文可兼有。

```bash
python -m arxiv_daily.library init
python -m arxiv_daily.library add --report /path/to/daily.md --indices 001,002 --list favorite
python -m arxiv_daily.library list --list deep-read --status unread
python -m arxiv_daily.library mark --ids 2610.00001 --status read
python -m arxiv_daily.library export
```

CSV 使用 UTF-8 BOM，Excel 可直接打开。主库是 SQLite；通过 dots 修改数据，CSV 是自动生成的查看/导出文件，手动编辑不会回写。新日报保存在独立批次目录，不会覆盖同一天另一份日报的编号。保留整个 `library/` 可备份或迁移文献库；不上传公开 GitHub，也不自动跨设备同步。源关键词缺失留空；网站查询日期、加入时间、来源日期原文分开记录，不冒充 arXiv 首次发表日期。更多命令见[持久文献库流程](skills/arxiv-daily-reader/references/LIBRARY.md)。
