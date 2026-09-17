# 阅读快照：2026-09-07；保留完整原文件，仅增加讲解注释。
# 原文件：/Users/gaoronghui/Documents/agent_learning/2-进行中/面试准备/项目准备/智能经营分析/实验/LangGraph经营分析面试复现/business_analysis_repro/main_agent/catalog.py
# 原文件 SHA-256：fbc2933a94cc266713eb74b32d02d39e06b18fcc23073acc5f9752797ac3ecb3
# 本副本用于阅读，不作为可独立运行的脚本；运行请使用原包的 python -m 入口。
# 搜索“剩余阅读”可定位还没按执行顺序讲完的部分；下文行号均指原文件。
# 配套摘要：../代码阅读摘要.md。注释是 Codex 的源码解读，不代表已验收你的理解。

"""指标定义：回答“它是什么”和“根据哪个配置查询”，不承载用户本次日期。

以下 ID、业务线、数据集、表名全是本实验的模拟配置，不能当成公司真实元数据。
指标身份和取数方式分开：相同的指标语义可以关联不同的查询后端。
本例为保费配置模拟指标平台，为保单量配置实际执行的本地 SQLite SQL。
"""

from copy import deepcopy

# ── 业务身份映射｜原文件 10 行 ──
# 这些 demo_ 开头的 ID 都是实验配置；业务名称和业务线 ID 是不同层次的字段。
BUSINESS_LINES = {"准时保": "demo_biz_timely", "运费险": "demo_biz_shipping"}

# ── 指标字典｜原文件 12–75 行 ──
# 你关心的名称、别名、标准 ID、含义、查询方式、数据集、业务线、SQL、表都在这里。
# 指标定义可以重复使用；某次请求的日期稍后才加入。
METRIC_CATALOG = {
    "premium": {
        "metric_id": "demo_metric_premium_income",
        "name": "保费收入",
        "english_name": "premium_income",
        "aliases": ["保费", "保费收入", "保险保费"],
        "definition": "模拟口径：有效保单的保费金额之和。",
        "unit": "元",
        "value_type": "amount",
        "formula": "SUM(premium_amount)",
        "supported_dimensions": ["业务", "日期", "渠道"],
        "time_basis": "承保日期，Asia/Shanghai，起止日期均包含",
        "source_grain": "业务 × 日期 × 渠道",
        "aggregation": "按业务、日期、渠道可加和；不跨币种混合",
        "analysis_scenarios": ["期间汇总", "环比分析", "渠道贡献分解"],
        # ── 保费的取数配置｜原文件 27–36 行 ──
        # 标准 metric_id 与平台 platform_metric_id 不必相同，映射由配置提供。
        # 平台底表没有配置，所以 source_tables 为空；不能从空值推断已经知道底表。
        "query": {
            "method": "metric_platform",
            "adapter": "local_metric_platform_fixture",
            "dataset_id": "demo_ds_insurance_daily",
            "platform_metric_id": "demo_platform_premium_amount",
            "business_line_ids": BUSINESS_LINES,
            "reference_sql_template": None,
            "source_tables": [],
            "source_note": "平台底表未配置；本实验由本地模拟接口生成数据，没有调用外部平台。",
        },
        "config_version": "demo-v2",
        "synthetic": True,
    },
    "policy_count": {
        "metric_id": "demo_metric_policy_count",
        "name": "保单量",
        "english_name": "policy_count",
        "aliases": ["保单量", "保单数", "有效保单数量"],
        "definition": "模拟口径：有效保单的数量。",
        "unit": "单",
        "value_type": "count",
        "formula": "SUM(policy_count)",
        "supported_dimensions": ["业务", "日期", "渠道"],
        "time_basis": "承保日期，Asia/Shanghai，起止日期均包含",
        "source_grain": "业务 × 日期 × 渠道的日汇总",
        "aggregation": "对日汇总保单量求和；此指标不是跨日用户去重数",
        "analysis_scenarios": ["期间汇总", "环比分析", "渠道贡献分解"],
        # ── 保单量的取数配置｜原文件 54–71 行 ──
        # SQL 模板固定，用户业务和日期作为绑定参数；没有让模型自由拼接 SQL。
        "query": {
            "method": "sql",
            "adapter": "local_sqlite_fixture",
            "dataset_id": None,
            "platform_metric_id": None,
            "business_line_ids": BUSINESS_LINES,
            "database": "本地 SQLite 内存库（每次调用重新装载模拟数据）",
            "source_tables": ["demo_insurance_daily"],
            "reference_sql_template": (
                "SELECT biz_date AS date, channel, SUM(policy_count) AS value\n"
                "FROM demo_insurance_daily\n"
                "WHERE business_line_id = :business_line_id\n"
                "  AND biz_date BETWEEN :start_date AND :end_date\n"
                "GROUP BY biz_date, channel\n"
                "ORDER BY biz_date, channel"
            ),
            "source_note": "这条 SQL 在本地 SQLite 实际执行；数据为程序生成的模拟日汇总数据。",
        },
        "config_version": "demo-v2",
        "synthetic": True,
    },
}

# ── 给理解模型看的小目录｜原文件 77–82 行 ──
# 只选择名称、单位、定义、别名；数据集和 SQL 等执行细节由后面的代码查配置。
# 给模型的小型语义目录不包含数据集/SQL 等物理细节。
# 业务含义由模型匹配；query 方法及具体参数由下面的代码查配置决定。
METRICS = {
    key: {field: item[field] for field in ["name", "unit", "definition", "aliases"]}
    for key, item in METRIC_CATALOG.items()
}


# ── 保存执行时的定义快照｜原文件 85–91 行 ──
# deepcopy 防止本次补充业务字段时修改共享目录；结果和 Trace 能保留当时配置。
def metric_snapshot(key: str, business: str | None = None) -> dict:
    """复制一份执行当时的定义写入证据，配置将来改变也不会改写历史 Trace。"""
    item = deepcopy(METRIC_CATALOG[key])
    item["catalog_key"] = key
    item["business"] = business
    item["query"]["business_line_id"] = BUSINESS_LINES.get(business)
    return item


# ── 本次查询实例｜原文件 94–119 行 ──
# 把标准定义与本次业务、日期组合成执行说明，再由 query_agent 实际消费。
# 查询配置本身不能证明执行过，所以结果还记录 request/executed_sql 和 execution_status。
def query_execution(task: dict) -> dict:
    """本次查询实例：这里才放日期和业务线取值，不修改共享指标定义。"""
    metric = metric_snapshot(task["metric"], task["business"])
    query = metric["query"]
    params = {
        "business_line_id": query["business_line_id"],
        "start_date": task["start_date"],
        "end_date": task["end_date"],
    }
    if query["method"] == "metric_platform":
        params.update(
            dataset_id=query["dataset_id"],
            metric_id=query["platform_metric_id"],
            group_by=["biz_date", "channel"],
        )
    return {
        "method": query["method"],
        "adapter": query["adapter"],
        "metric_id": metric["metric_id"],
        "config_version": metric["config_version"],
        "parameters": params,
        "sql_template": query["reference_sql_template"],
        "source_tables": query["source_tables"],
        "synthetic": True,
        "execution_note": query["source_note"],
    }
