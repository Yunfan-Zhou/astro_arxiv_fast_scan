# 持久收藏与精读列表

同一固定输出工作区共用一份 `library/papers.sqlite3` 主库，自动导出 `library/papers.csv`（UTF-8 BOM，Excel 可直接打开）。每次添加都是合并已有记录，不按日期清空。CSV 是可读导出；请通过 dots 修改状态和备注，直接编辑 CSV 不会自动回写主库。

## 按日报序号加入

用户说“把001、002加入精读/收藏列表”时，先确定他所指的 Markdown：当前对话刚交付的报告可以直接使用；若他指出旧日报或附了文件，使用那份文件。不能因为 `data/latest.json` 更新而换成最新日报。没有可确定的报告时，询问对应文件或日期，不能猜编号。

新报告路径为 `reports/日期/批次哈希/daily.md`，旁边有 `paper-index.json`，应一并保留。程序验证日报批次、显示编号与 arXiv ID/版本，旧日报也可通过工作区内的历史数据批次定位。不同日期的001不代表同一论文。

```bash
<Python> <技能目录>/scripts/run.py library add --report <所读daily.md绝对路径> --indices 001,002 --list deep-read --note '可选备注'
<Python> <技能目录>/scripts/run.py library add --report <所读daily.md绝对路径> --indices 001,002 --list favorite
```

序号支持英文逗号、中文逗号和顿号。精读列表与收藏是独立标记，同一论文可同时属于两者。加入精读列表不等于开始精读，不擅自启动全文阅读。添加成功后回复实际论文编号、标题、arXiv ID，以及新增/合并数量和 CSV 链接。不要只有一句“已收藏”。

## 持久数据规则

- 按 arXiv ID 去重。同一论文新版更新元数据并保留原加入时间、备注、阅读状态和日报来源历史；旧日报不会把新版本降级。
- 新备注追加，重复备注不重复写入。再次收藏不会把“已读”重置为“未读”。
- 保存原题、中文标题（若已有）、作者、URL/PDF URL、版本、分类、来源关键词、摘要、评论、来源日期原文、首次/最近出现的日报日期、加入/更新时间、收藏/精读标记、阅读状态、备注和报告来源。
- “日报日期”“加入时间”和“来源日期原文”分列；没有核验的 arXiv 首次提交/修改日期不编造。源站未给关键词时留空并保留缺失标记，不伪造作者关键词。
- SQLite 事务避免两个任务同时追加时丢记录；CSV 每次从完整主库原子导出。导出失败后可重试 export，不需要重读论文。
- 旧版 `favorites.json` 首次使用自动迁移；之后仍导出这个兼容文件。不要手动用 JSON/CSV 覆盖主库。
- 个人库位于 `.gitignore` 排除的 `library/`，不推送到公开 GitHub。迁移机器时保留整个 library 目录，以及历史报告和索引；两个设备的库不会自动同步。

## 后续挑出精读

```bash
# 查看精读队列中的未读论文；返回持久ID和完整文献信息
<Python> <技能目录>/scripts/run.py library list --list deep-read --status unread --limit 20
# 查看收藏，或不加过滤列出所有入库论文
<Python> <技能目录>/scripts/run.py library list --list favorite
# 用户确认开始阅读或实际完成后再更新状态
<Python> <技能目录>/scripts/run.py library mark --ids 2610.00001 --status reading
<Python> <技能目录>/scripts/run.py library mark --ids 2610.00001 --status read
# 初始化空库，或从主库重新导出CSV
<Python> <技能目录>/scripts/run.py library init
<Python> <技能目录>/scripts/run.py library export
```

状态：`unread` 未读、`reading` 阅读中、`read` 已读。从精读队列挑论文时使用返回的 arXiv ID，不把队列行号当日报序号。真正精读时遵循适用的精读技能（本工作区是 paper-deep-report），完成后将结果路径写入备注或后续记录。

浏览器 reader.html 的星标依然保存在浏览器中，不会自动写入此主库；要使用持久库，向 dots 发上述加入命令。也不能把只勾选 Markdown 复选框声称为数据库已更新。
