# 用 dots 运行论文速览与持久文献库

## ChatGPT dots：直接在它的云电脑运行

ChatGPT 的 dot 自带云电脑和浏览器，可以在用户电脑关机后工作，并在多次使用之间保留状态；本机访问是可选项。本机安装的技能不会因此自动成为云端可用文件。[OpenAI 官方说明](https://learn.chatgpt.com/docs/dots/computers-and-apps)

本项目的云端使用方式是让 dot 克隆仓库，读取仓库中的 SKILL.md 并运行代码，不依赖它自动发现 Mac 上的本地技能。首次把下面这段发给 dot：

> 请在你的云电脑中，将 ~/astro_arxiv_fast_scan/ 作为本项目专用目录。从 https://github.com/Yunfan-Zhou/astro_arxiv_fast_scan 克隆代码到这个目录下的 code/，读取 skills/arxiv-daily-reader/SKILL.md。固定使用这个目录下的 state/ 保存日报和持久文献库，以后继续复用，不能每天新建一份数据库。请使用云端可用的 Python；依赖放在本项目目录内的虚拟环境。默认只保留 astro-ph.GA 或 astro-ph.CO（含交叉分类），每篇详细读摘要并实际读取1–2张关键图，每张附科学讲解。阅读子 agent 优先使用 GPT-6.1 Sol、medium；如果不能指定，说明实际模型。先完成初始化并告诉我固定路径；以后我说“当天 arXiv 论文速览”就按这个工作流执行，我说“把001、002加入收藏/精读列表”就按对应日报索引更新同一文献库并导出 CSV。不要将个人库推送到公开 GitHub，也不要自行创建定时任务。

这段指令指定了云端代码和数据的工作范围。dot 应在其实际云环境中检查可用工具、网络、模型及目录后执行；本仓库不声称已经代用户在 dot 云端部署完成，也不承诺任意临时子任务环境共享同一磁盘。若使用隔离的子任务，成果必须收回同一 state/，不要把临时目录当作主库。

供 dot 执行的初始化示例（仅在上述专用目录中；已有仓库/环境时先检查并复用）：

```bash
arxiv_workspace="$HOME/astro_arxiv_fast_scan"
mkdir -p "$arxiv_workspace"
git clone https://github.com/Yunfan-Zhou/astro_arxiv_fast_scan.git "$arxiv_workspace/code"
python3 -m venv "$arxiv_workspace/.venv"
"$arxiv_workspace/.venv/bin/python" -m pip install "$arxiv_workspace/code[figures]"
"$arxiv_workspace/.venv/bin/python" "$arxiv_workspace/code/skills/arxiv-daily-reader/scripts/run.py" --workspace "$arxiv_workspace/state" library init
```

调用 `start`、`finish`、`library` 时均使用相同的 `--workspace`。云端用云端 Python，不要复制 Mac 的 myenv 路径或本机 local.json。代码更新与 state/ 分离；备份整个 state/library/ 可以保留积累的数据，日报及 paper-index.json 也应保留。

## 可选：本机 Codex 或其他支持技能目录的环境

本机安装器仍可使用：

```bash
python scripts/install_skill.py --destination "<实际技能目录>/arxiv-daily-reader" --workspace "<固定文献工作区>"
```

使用本机指定的 myenv（如有）。安装器附带完整运行代码，已有同名目录时停止以避免覆盖。让相应客户端加载该 SKILL.md。本机与云端是不同文件系统，不能假设安装或文献库自动同步。

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
