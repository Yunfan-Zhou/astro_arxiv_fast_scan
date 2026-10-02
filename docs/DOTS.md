# 用 dots 运行论文速览与持久文献库

## 安装一次

先把 [仓库](https://github.com/Yunfan-Zhou/astro_arxiv_fast_scan) 放到运行 dots 的机器上：

```bash
git clone https://github.com/Yunfan-Zhou/astro_arxiv_fast_scan.git
cd astro_arxiv_fast_scan
python scripts/install_skill.py --destination "<dots实际技能目录>/arxiv-daily-reader" --workspace "<固定文献工作区>"
```

`python` 使用该机器的 Python 3.11+；用户有指定 myenv 时使用其完整路径。读图所需模块为 pypdf、pypdfium2、Pillow；先检查是否已安装，缺少时在对应环境安装 `pip install '.[figures]'`。不要把示例中的尖括号路径直接当成真实目录。

让 dots 加载安装目录中的 `SKILL.md`。安装器把运行代码和参考文件一起复制；之后无需依赖原仓库位置。已有同名安装器会停止，防止覆盖自定义配置。

不同产品的 dots 技能入口可能不同，本项目未验证你使用的 dots 产品的安装界面。需要它能读取 SKILL.md、执行 Python、联网获取论文、调用有视觉能力的模型，并写入固定工作区。同一台机器上的 Codex/dots 可指向同一个 workspace 共用文献库；另一台机器须自行安装和迁移所需资料，不会自动共享本机文件。

不清楚技能安装入口时，可以先在 dots 中明确说：

> 请读取我本地 astro_arxiv_fast_scan 仓库里的 skills/arxiv-daily-reader/SKILL.md，并按这个技能执行。固定使用我指定的文献工作区保存报告和文献库，以后继续使用同一目录。

此方式仍要求 dots 能访问该目录并运行代码；不是仅打开 GitHub 网页就能自动执行。

## 日常怎么说

> 我想进行当天最新的 arxiv 论文速览。

默认规则已经写进技能，无需每次重述：主分类或交叉分类含 astro-ph.GA（星系）或 astro-ph.CO（宇宙学）就保留；New submissions、Cross-lists、Replacements 都包含。Sol 中推理子 agent 分批详细解读摘要，每篇选择1–2张关键图，实际看图并解释坐标、趋势、数值、限制和与论文结论的关系；交付 Markdown、图片附件及实际可取得的 token 用量。

日报路径含日期和批次哈希，不会因为同一天重新筛选而覆盖另一批论文的编号。收到报告时保留旁边的 `paper-index.json` 和引用的图片文件。

## 看完 Markdown 后怎么保存

在同一对话中说：

> 把这份日报的001、002加入精读列表，备注：后续重点看方法与误差分析。

或者：

> 收藏这份日报的001、005。

对旧日报或新对话，附上对应 daily.md 的路径/文件，避免001指向另一份报告。dots 会将新增文献合并到固定工作区的 `library/papers.csv`；它能直接用 Excel 打开。一次加入多篇、以后继续追加、同一论文重复加入都支持。精读列表与收藏是独立标记，可以同时拥有。加入列表只做记录，不立即开始全文精读。

保存字段包括论文名称、中文标题（已有时）、作者、URL/PDF URL、版本、分类、来源关键词、摘要、评论、来源日期原文、首次/最近日报日期、加入/更新时间、收藏/精读标记、状态、备注及来源报告。关键词缺失留空并标注缺失，不伪造。

后台主库为 `library/papers.sqlite3`，CSV 自动从完整主库更新。重复论文按 arXiv ID 合并，新版本不会清除原备注和已读状态。直接编辑 CSV 不会回写主库，修改信息请告诉 dots。整个 `library/` 是长期积累的数据目录，不按天清空，且不上传公开 GitHub。

## 从积累中挑出来精读

> 列出精读列表中尚未读过的前10篇。

> 从精读列表中取出 arXiv:2610.00001，进行精读。

> 把 arXiv:2610.00001 标记为已读，备注里保存精读报告路径。

真正精读时使用所在环境适用的精读技能；本工作区按用户要求使用 paper-deep-report。执行成功后才标记已读。持久命令与数据库规则详见[文献库说明](../skills/arxiv-daily-reader/references/LIBRARY.md)。

## 命令入口（供 dots 执行）

```bash
python <技能目录>/scripts/run.py status
python <技能目录>/scripts/run.py start
# 由 agent 完成摘要与图表解读后
python <技能目录>/scripts/run.py finish
python <技能目录>/scripts/run.py library add --report /path/to/daily.md --indices 001,002 --list deep-read
python <技能目录>/scripts/run.py library list --list deep-read --status unread --limit 10
python <技能目录>/scripts/run.py library mark --ids 2610.00001 --status read --note /path/to/deep-reading.md
```

代码负责抓取、筛选、组装和保存；阅读由 dots 的模型能力完成。如果无法使用指定子 agent 或模型，必须说明实际能力，不能声称已按指定模型读过。仓库按需执行，不默认创建定时任务或自动精读收藏。GitHub Actions 的手动工作流只生成元数据和待阅读报告，不调用模型。

reader.html 的浏览器星标是另一份本地存储，不自动写入 SQLite/CSV；需要持久文献库时，向 dots 发“加入收藏/精读列表”命令。
