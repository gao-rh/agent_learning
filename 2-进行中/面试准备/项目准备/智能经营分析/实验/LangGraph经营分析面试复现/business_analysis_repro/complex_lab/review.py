"""私有离线评审：从不被模型执行路径调用，不把检查结果回灌成标准答案。"""

from .knowledge import FIXTURES
from .runtime import read, write


def evaluate(case_id, record):
    rubric = read(FIXTURES / "rubrics.private.json")["cases"][case_id]
    plan = record.get("resolver_result", {})
    turn = record["turn_number"]
    tasks = plan.get("tasks", [])
    reqs = plan.get("requirements", [])
    checks = []

    def check(label, passed, expected=None, actual=None):
        checks.append(
            {"label": label, "passed": bool(passed), "expected": expected, "actual": actual}
        )

    def all_tasks(label, fn):
        check(label, bool(tasks) and all(fn(t) for t in tasks))

    def period(t, start, end):
        return t.get("period") == {"start": start, "end": end}

    def baseline(t, start, end):
        return t.get("comparison_period") == {"start": start, "end": end}

    def views(x):
        return {(v["kind"], tuple(v.get("months", []))) for v in x.get("views", [])}

    def metrics():
        return {t.get("metric_id") for t in tasks}

    def keywords(text, groups):
        return all(any(k in text for k in group) for group in groups)

    def predicates(t):
        return {(p["field"], p["op"], str(p["value"])) for p in t.get("predicates", [])}

    expected_outcome = rubric["outcomes"][turn - 1]
    check(
        "决定是否正确",
        plan.get("outcome") == expected_outcome,
        expected_outcome,
        plan.get("outcome"),
    )
    check(
        "公开契约校验",
        record.get("validation", {}).get("accepted", False),
        [],
        record.get("validation", {}).get("errors", []),
    )
    check(
        "执行未失败",
        record.get("status") == "waiting_review",
        "waiting_review",
        record.get("status"),
    )
    if case_id == "C01":
        needed = {("month", ()), ("year", ()), ("annual_months", tuple(range(1, 8)))}
        covered = {(r.get("metric_id"), v) for r in reqs for v in views(r)}
        original = {(mid, v) for mid in rubric["original_metrics"] for v in needed}
        check("原七类输出乘三类时间视图完整", original <= covered, 21, len(original & covered))
        gaps = [
            r for r in reqs if r.get("metric_id") in {"cx_timely_merchant", "cx_timely_platform"}
        ]
        check(
            "付费方缺口明确保留",
            len(gaps) == 2 and all(r["status"] in {"gap", "pending"} for r in gaps),
        )
        if tasks:
            all_tasks(
                "统计期间保持2021年至2026年8月", lambda t: period(t, "2021-01-01", "2026-08-31")
            )
            all_tasks("各任务保留三种视图", lambda t: needed <= views(t))
        check(
            "报告和Wiki均为计划",
            {"report", "wiki"} <= {d["type"] for d in plan.get("delivery", [])}
            and all(d["status"] in {"planned", "blocked"} for d in plan.get("delivery", [])),
        )
        if turn == 2:
            check(
                "接受替代后的六类输出正确",
                metrics() == set(rubric["final_metrics"]),
                rubric["final_metrics"],
                sorted(metrics()),
            )
            replacements = {
                r["id"]
                for r in reqs
                if r.get("metric_id") == "cx_timely_food" and r["status"] == "active"
            }
            check(
                "两项缺口关联用户接受的替代",
                bool(replacements)
                and all(replacements & set(r.get("replacement_ids", [])) for r in gaps),
            )
            check(
                "2026年未满年度明确标注",
                any(
                    keywords(
                        v.get("note", ""),
                        [["2026"], ["8", "八"], ["不满", "未满", "截至", "覆盖", "仅"]],
                    )
                    for t in tasks
                    for v in t["views"]
                    if v["kind"] == "year"
                ),
            )
    elif case_id == "C02":
        if turn >= 2:
            check(
                "结果目标和四个观察指标完整",
                set(rubric["final_metrics"]) <= metrics(),
                rubric["final_metrics"],
                sorted(metrics()),
            )
            all_tasks("保留钱包渠道", lambda t: t.get("filters", {}).get("channel") == ["wallet"])
            all_tasks("保留本期8月24至30日", lambda t: period(t, "2026-08-24", "2026-08-30"))
            all_tasks("保留基期8月17至23日", lambda t: baseline(t, "2026-08-17", "2026-08-23"))
            all_tasks(
                "保留渠道曝光人群",
                lambda t: keywords(t.get("population", ""), [["曝光"], ["钱包", "渠道"]]),
            )
            check(
                "商户类型观察方向仍保留",
                any("merchant_type" in t.get("group_by", []) for t in tasks),
            )
        if turn == 3:
            new_tasks = [
                t
                for t in tasks
                if "merchant_age" in t.get("group_by", []) or "merchant_age" in t.get("filters", {})
            ]
            check("增加新老商比较", bool(new_tasks))
            check(
                "新商按曝光日距入驻30天",
                bool(new_tasks)
                and all(
                    keywords(t.get("cohort_rule", ""), [["曝光"], ["入驻", "注册"], ["30", "三十"]])
                    for t in new_tasks
                ),
            )
    elif case_id == "C03":
        check(
            "五项指标准确无遗漏或增加",
            metrics() == set(rubric["final_metrics"]),
            rubric["final_metrics"],
            sorted(metrics()),
        )
        all_tasks("全部本期为8月", lambda t: period(t, "2026-08-01", "2026-08-31"))
        all_tasks("全部基期为7月", lambda t: baseline(t, "2026-07-01", "2026-07-31"))
        all_tasks(
            "安徽江苏与餐饮范围逐项保留",
            lambda t: (
                set(t.get("filters", {}).get("province", [])) == {"anhui", "jiangsu"}
                and t.get("filters", {}).get("business_segment") == ["food"]
            ),
        )
        all_tasks(
            "省份与城市经营类型为组合分组",
            lambda t: set(t.get("group_by", [])) == {"province", "city_operation"},
        )
        all_tasks(
            "取消单排除只施加于保险订单",
            lambda t: (
                (("order_status", "ne", "cancelled") in predicates(t))
                == (t["metric_id"] == "cx_fx_orders")
            ),
        )
        check("没有向用户重复澄清", not plan.get("questions"))
    elif case_id == "C04":
        check(
            "实际读取两版正式定义和重算能力",
            {"K-CANCEL-V1", "K-CANCEL-V2", "K-RECOMPUTE"} <= set(plan.get("knowledge_refs", [])),
        )
        if turn == 2:
            historic = [t for t in tasks if t.get("comparison_mode") == "historical_display"]
            comparable = [t for t in tasks if t.get("comparison_mode") == "same_definition"]
            assignments = set()
            for t in historic:
                assignments.add((t["period"]["start"], t["definition_version"]))
                if t.get("comparison_period"):
                    assignments.add((t["comparison_period"]["start"], t["baseline_version"]))
            check(
                "历史6月旧版、7月新版",
                assignments == {("2026-06-01", "v1"), ("2026-07-01", "v2")},
                [["2026-06-01", "v1"], ["2026-07-01", "v2"]],
                sorted(assignments),
            )
            check(
                "历史组不当作重算", bool(historic) and all(not t.get("recompute") for t in historic)
            )
            check(
                "另列统一新版重算组",
                bool(comparable)
                and all(
                    period(t, "2026-07-01", "2026-07-31")
                    and baseline(t, "2026-06-01", "2026-06-30")
                    and t["definition_version"] == t["baseline_version"] == "v2"
                    and t["recompute"]
                    for t in comparable
                ),
            )
            all_tasks(
                "各组保持取消险指标与省份分组",
                lambda t: t["metric_id"] == "cx_cancel_rate" and t["group_by"] == ["province"],
            )
            check("任务全部属于历史或可比组", len(historic) + len(comparable) == len(tasks))
    failed = [c for c in checks if not c["passed"]]
    return {
        "grade": "failed" if failed else "pending_human_review",
        "expected_outcome": expected_outcome,
        "checks": checks,
        "mismatches": failed,
        "question_topics": rubric.get("question_topics", []) if turn == 1 else [],
        "human_review": None,
        "note": "自动检查只覆盖明确结构约束；问句语义、无证据结论、替代接受和完整业务含义需人工审阅。",
    }


def review_turn(folder, number, *, human_passed=None, notes=""):
    record = read(folder / f"turn-{number}.json")
    result = evaluate(record["case_id"], record)
    if human_passed is not None:
        result["human_review"] = {
            "passed": human_passed,
            "notes": notes,
            "reviewer": "Codex基于实际外显记录人工式审阅，非独立LLM裁判",
        }
        if result["grade"] != "failed":
            result["grade"] = (
                ("clarify" if record["resolver_result"].get("outcome") == "clarify" else "passed")
                if human_passed
                else "failed"
            )
    write(folder / f"review-{number}.json", result)
    return result
