"""指标定义：回答“它是什么”和“根据哪个配置查询”，不承载用户本次日期。

以下 ID、业务线、数据集、表名全是本实验的模拟配置，不能当成公司真实元数据。
指标身份和取数方式分开：相同的指标语义可以关联不同的查询后端。
本例为保费配置模拟指标平台，为保单量配置实际执行的本地 SQLite SQL。
"""

from copy import deepcopy

BUSINESS_LINES = {"准时保": "demo_biz_timely", "运费险": "demo_biz_shipping"}

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

# 给模型的小型语义目录不包含数据集/SQL 等物理细节。
# 业务含义由模型匹配；query 方法及具体参数由下面的代码查配置决定。
METRICS = {
    key: {field: item[field] for field in ["name", "unit", "definition", "aliases"]}
    for key, item in METRIC_CATALOG.items()
}


def metric_snapshot(key: str, business: str | None = None) -> dict:
    """复制一份执行当时的定义写入证据，配置将来改变也不会改写历史 Trace。"""
    item = deepcopy(METRIC_CATALOG[key])
    item["catalog_key"] = key
    item["business"] = business
    item["query"]["business_line_id"] = BUSINESS_LINES.get(business)
    return item


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
