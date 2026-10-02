"""Shared reading contract; bump its version when cached output becomes incompatible."""

READING_STYLE = "detailed-v2"
FIGURE_POLICY = "key-figures-v1"
DEFAULT_BATCH_SIZE = 8
SECTIONS = (
    ("problem", "1. 研究背景和问题定义"),
    ("method", "2. 主要方法和创新点"),
    ("result", "3. 关键结果和贡献"),
    ("meaning", "4. 潜在应用和意义"),
)
DEPTH_GUIDANCE = """四项正文合计通常约800–1400汉字，以信息完整为先；摘要信息少时可短于目标，不凑字数。
problem：交代研究对象、背景、尚未解决的问题及本文具体要回答什么。
method：解释数据/样本、观测或模型、关键步骤及其作用；只有摘要支持时才谈相对已有工作的创新。
result：逐项说明主要发现，保留数值、单位、不确定性、比较对象及适用条件，并解释结果回答了什么问题。
meaning：区分作者提出的意义与明确标注的合理推断，说明适用范围、尚不能得出的结论及值得精读的线索。
每部分用1–3个自然段，可用空行分隔；字段内使用纯文本，不重复小节标题。避免四句式压缩、空泛赞美、重复结论。
正文优先解释论文在做什么、方法为什么有用、结果意味着什么；缺失细节集中放在limitation，避免每节罗列“摘要未说明”或“不能断言”来凑篇幅。影响核心结论的条件仍随结论保留。
没有提供的方法细节、结果或验证证据写“摘要未说明”；不虚构数字、因果关系、创新优先权或图表内容。
通用概念解释应与本文事实分开；不要仅凭题目扩写背景。用Unicode/纯文本表达数学量，不输出裸LaTeX命令。"""


def format_reading(item):
    content = ["### " + item["title_zh"], "以下四节依据标题、摘要与评论/说明；图表证据及阅读状态另列。"]
    for field, heading in SECTIONS:
        content.extend(["#### " + heading, item[field]])
    if item["limitation"]:
        content.extend(["#### 阅读限制与来源质量", item["limitation"]])
    return "\n\n".join(content) + "\n"
