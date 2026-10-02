# 来源接口与可靠性

2026-10-02 从用户指定的 [Giiisp 页面](https://www.giiisp.com/#/arxiv?subjectId=1399191569822654465&arxivFilterTimelineSelected=1) 的公开前端确认：

- `GET /first/arxiv/arxivSubject`：该 subjectId 是 level=2 的 Astrophysics。
- `GET /first/arxiv/arxivPaperList/checkForArxivUpdates?subjectId=...`：前端把 empty="1" 显示为更新中，empty="2" 显示为更新完毕。没有保证该状态携带日期。
- `POST /first/arxiv/arxivPaperList`：查询参数包含 pageNum、pageSize、level、startDate、endDate、getLatest 等；JSON body 是 `[{"subjectId":"...","arxivType":"1"}]`。
- arxivType 1/2/3 分别对应 New submissions / Cross-lists / Replacements。
- 原字段：`arvixNo`（网站拼写如此）、`version`、`title`、`author`、`paperAbstract`、`keyWord`、`comments`、`subjects`。

前端文件：`app.2e201f49489e790cfee7.js`、`18.c509e2f93fde7770320c.js`。这些名称会随网站发布变化；运行代码不依赖文件名。

实测 pageSize=2 返回 total=2，pageSize=50 返回 total=50，因此程序不将 total 当作总体数量或总页数。即使某页不足 pageSize，也继续请求直到空页。重复页、分页上限、字段缺失或不同列表的元数据冲突均报错，不发布部分数据。

首页“最新”可能指向上一次更新。程序使用 getLatest=0 且 startDate=endDate=北京时间查询日，保留相对 releaseDate 标签原值，不把 today 直接解释为 arXiv 提交日期。更新状态在采集前后检查，并比较两轮完整结果；这是稳定性检查，无法保证网站未来不再修订。

周末/休刊日仍检查来源，不臆测放假规则。来源已完成且日期列表为空时发布明确的空批次；未完成则退出 3，保留上次快照。消费者必须检查 query_date。

仅持久化元数据和阅读 prompt，不保存接口中附带的图、全文、邮箱、分享用户等信息。作者保留原始字符串，避免简单拆逗号破坏姓名或合作组。网站原文可能有乱码，代码不猜测修复。关键词缺失不以学科分类冒充。

接口为网站公开前端所用接口，并非承诺稳定的官方开发者 API。网络、站点规则或 schema 变化可能导致抓取失败；程序明确报错，不绕过登录或切换成不同筛选范围。
