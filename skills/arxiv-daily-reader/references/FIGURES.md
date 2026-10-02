# 只读关键图表

这一流程由有视觉阅读能力的 dots/agent 执行。抓取器本身不会假装读图，也不会自动把所有图下载进日报。

1. 先读标题和摘要，判断哪篇的关键结论依赖图表（结果趋势、关键对照、观测图、参数约束等）。优先处理与用户兴趣最相关的论文，默认一天最多 5 篇、每篇最多 2 张图或表；在日报写明实际看了哪些和未看的范围。
2. 下载所选论文的原始 PDF（`papers.json` 中的 `pdf_url`；也可由 arXiv 链接进入 PDF），保存 `cache/`。不得从低分辨率截图二次裁切。仅作本地缓存，不提交整个 PDF。
3. 扫描候选图注与引用，不把正文引用当作已找到图：

   ```bash
   python <技能目录>/scripts/run.py figures inspect cache/paper.pdf --output cache/candidates.json
   python <技能目录>/scripts/run.py figures render cache/paper.pdf --page 4 --output cache/page-4.png
   ```

4. 实际打开原页图像后，创建裁切计划。坐标是固定 scale=3（216 dpi）渲染后的像素，页码从 1 开始。完整保留标题、所有 panel、全部坐标刻度/单位、图例、色标、误差棒、科学标注及完整 Figure/Table 编号与图注；不混入页眉页码、正文或相邻图。多页图可在正文引用原 PDF，不能将不完整部分冒称完整图。

   ```json
   {"figures":[{"name":"figure_1","page":4,"bbox":[100,200,1700,1400],"selection_reason":"检验摘要中的核心趋势","required_elements":["所有面板","横纵坐标与单位","图例","误差棒","完整 Figure 1 图注"]}]}
   ```

   这里坐标仅示意，必须根据该 PDF 实际页面填写。计划保存到 `reports/assets/<task_id>/plan.json`。

   ```bash
   python <技能目录>/scripts/run.py figures crop cache/paper.pdf --plan reports/assets/TASK_ID/plan.json --output reports/assets/TASK_ID
   ```

5. 逐张打开最终 PNG 视觉验收，截断或混入正文就修改计划重裁。输出自动添加 12 px 白边，manifest 记录 PDF/图片哈希、页码、比例、尺寸、框坐标及验收状态。只有看过最终 PNG，才将对应 `visually_verified` 改为 true，并填写具体 `verification_note`。重裁自动撤销旧验收。
6. 在 `reports/papers/<task_id>.md` 加“关键图表解读”：图号/页码、变量与单位、图例、趋势或数值、误差与限制、与摘要结论的关系。不能从曲线估读出不存在的高精度数值，不能只看图注就声称看过图。分清摘要证据与图表证据。
7. `python <技能目录>/scripts/run.py report` 汇总单个 Markdown 日报，并自动嵌入已验收图表；图片文件须一起保留。需要 Codex 本地预览的绝对图片路径时使用 `--absolute-images`，发布 GitHub 前重新运行默认命令恢复可移植相对链接。

可选依赖：`python -m pip install '.[figures]'`。已有 myenv 应先验证依赖并显式使用其 Python。PDF 只逐页渲染，避免整篇图像同时驻留内存。缺少视觉能力、PDF 无法获取或图不可读时，明确标注未核验，不补造解读。
