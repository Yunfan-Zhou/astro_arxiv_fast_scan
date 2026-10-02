# 给 dots 的最短入口

先克隆 [仓库](https://github.com/Yunfan-Zhou/astro_arxiv_fast_scan)，执行 `python scripts/install_skill.py --destination <dots实际技能目录>/arxiv-daily-reader --workspace <输出目录>`，再让 dots 加载该目录的 SKILL.md。安装器把运行代码和参考文件一并复制，不依赖原仓库路径。尚未在你的 dots 产品中验证加载入口；支持标准 SKILL.md 且可以运行 Python 的环境可使用。

之后说：

> 我想进行当天最新的 arxiv 论文速览。

技能会自动开始抓取、分批调用 Sol 中推理子 agent、按四个小节详细解读摘要（通常每篇800–1400汉字，信息少时更短），生成 Markdown 并报告可取得的实际 token。不必每次重述流程；也可显式调用 `$arxiv-daily-reader`。

后续操作：

- “收藏第 12 篇，备注：以后看中子星模型。”
- “把我收藏的论文列出来。”
- “对第 15 篇补看一两张关键图，图像 token 单独记录。”
- “精读我收藏的某篇论文。”——这是后续任务，不混入每日简报。

代码只抓取元数据、分批、组装报告和记录收藏，不调用付费模型。阅读由 dots 已有的模型能力执行；如果无法使用指定子 agent，必须说明实际模型。

仓库为按需模式，不默认启动每日阅读。GitHub Actions 手动工作流只生成元数据和报告容器作为运行附件，没有模型 key 时不会自动生成中文总结。

reader.html 支持搜索、星标、导出/导入收藏。浏览器收藏与 `library/favorites.json` 是两个独立存储位置，不自动同步。需要交给 dots 时导出 JSON/Markdown。本地收藏默认被 .gitignore 排除，不上传公开仓库。

只读环境可读取已有 Markdown；要抓取和保存收藏，需要 Python 3.11+ 和工作区读写权限。此处没有假定 dots 专有 API。
