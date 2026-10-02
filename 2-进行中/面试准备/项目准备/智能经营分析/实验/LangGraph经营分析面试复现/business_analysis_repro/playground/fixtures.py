"""提前生成的固定模拟数据。每指标独立立方体；不承诺跨指标事实一致。"""

import fcntl
import hashlib
import itertools
import json
import sqlite3
from contextlib import closing, contextmanager
from datetime import date, timedelta
from functools import lru_cache
from pathlib import Path
from threading import RLock

from ..settings import PROJECT_DIR
from .catalog import DIMENSIONS, METRICS

DATA_LOCK = RLock()
DATA_VERSION = "playground-cubes-v1"
START, END = date(2026, 1, 1), date(2026, 12, 31)
COLUMNS = ["metric_id", "biz_date", *sorted(DIMENSIONS), "numerator", "denominator"]


def distribute(total, weights):
    """整数最大余数分配：切分后仍精确等于预设总量，避免计数出现半个商户。"""
    denominator = sum(weights)
    parts = [total * w // denominator for w in weights]
    order = sorted(range(len(weights)), key=lambda i: -(total * weights[i] % denominator))
    for i in order[: total - sum(parts)]:
        parts[i] += 1
    return parts


def fixture_rows(metric, start, end):
    dims = list(metric["dimensions"])
    combos = list(itertools.product(*metric["dimensions"].values()))
    # 两个层级同时存在时，只生成真实的父子组合。
    combos = [
        c
        for c in combos
        if not {"channel_l1", "channel_l2"}.issubset(dims)
        or c[dims.index("channel_l1")]
        == DIMENSIONS["channel_l2"]["parent_values"][c[dims.index("channel_l2")]]
    ]
    day = start
    while day <= end:
        phase = "current" if day >= date(2026, 8, 24) else "baseline"
        preset = metric["preset"]
        # 周预设可不是7的倍数，按周内日序分配余数，整周依然精确闭合。
        n_week, d_week = preset[phase + "_numerator"], preset[phase + "_denominator"]
        n_day = n_week // 7 + (day.weekday() < n_week % 7)
        d_day = d_week // 7 + (day.weekday() < d_week % 7) if d_week else None
        weights = [
            1 + int(hashlib.sha256((phase + repr(c)).encode()).hexdigest()[:4], 16) % 5
            for c in combos
        ]
        nums = distribute(n_day, weights)
        if d_day is not None:
            # 分母由分子+剩余量组成，保持比例<=100%，且各组权重不同。
            rest = distribute(d_day - n_day, list(reversed(weights))) if d_day >= n_day else None
            dens = (
                [n + r for n, r in zip(nums, rest)]
                if rest is not None
                else distribute(d_day, weights)
            )
        else:
            dens = [0] * len(combos)
        for c, n, denominator in zip(combos, nums, dens):
            yield {
                "metric_id": metric["id"],
                "biz_date": day.isoformat(),
                **dict(zip(dims, c)),
                "numerator": n,
                "denominator": denominator,
            }
        day += timedelta(days=1)


def specification():
    digest = hashlib.sha256(Path(__file__).read_bytes())
    digest.update(json.dumps({"metrics": METRICS, "dimensions": DIMENSIONS},
                             sort_keys=True).encode())
    return {"data_version": DATA_VERSION, "fingerprint": digest.hexdigest(),
            "start": START.isoformat(), "end": END.isoformat(), "metrics": len(METRICS),
            "grain": "每指标×日×该指标的合法维度组合；计数为累计户次，非跨日商户去重",
            "cross_metric_consistency": False}


@lru_cache(maxsize=8)
def verified_digest(path, size, modified, changed):
    # 文件改动会改变 cache key；每次查询不用重新散列整份不可变数据库。
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


@contextmanager
def data_lock(directory):
    # 普通并行查询应等待第一次造数；不能套用任务执行的“冲突立即拒绝”锁。
    with DATA_LOCK, (directory / ".prepare.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(lock, fcntl.LOCK_UN)


def prepare_data(root=None):
    root = Path(root) if root is not None else PROJECT_DIR / ".runs" / "fixtures"
    spec = specification()
    directory = root / spec["fingerprint"][:16]
    directory.mkdir(parents=True, exist_ok=True)
    path, manifest = directory / "synthetic.sqlite", directory / "manifest.json"
    with data_lock(directory):
        if path.exists() or manifest.exists():
            if not (path.exists() and manifest.exists()):
                raise ValueError("模拟数据不完整；请保留现场并使用新的数据目录")
            metadata = json.loads(manifest.read_text())
            if metadata["specification"] != spec:
                raise ValueError("模拟数据版本不一致；拒绝覆盖旧数据")
            stat = path.stat()
            actual = verified_digest(str(path), stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns)
            if actual != metadata["database_sha256"]:
                raise ValueError("模拟数据库已被修改；拒绝把改动数据当成原固定数据")
            return {**metadata, "database": str(path.resolve()), "manifest": str(manifest.resolve())}
        temporary = directory / "synthetic.tmp"
        counts = {}
        temporary.unlink(missing_ok=True)
        try:
            with closing(sqlite3.connect(temporary)) as db:
                db.execute("CREATE TABLE demo_metric_daily (" + ",".join(COLUMNS) + ")")
                insert = "INSERT INTO demo_metric_daily VALUES (" + ",".join("?" for _ in COLUMNS) + ")"
                for metric in METRICS.values():
                    rows = list(fixture_rows(metric, START, END))
                    db.executemany(insert, [[r.get(c) for c in COLUMNS] for r in rows])
                    counts[metric["id"]] = len(rows)
                db.execute("CREATE INDEX metric_dates ON demo_metric_daily(metric_id,biz_date)")
                db.commit()
                if db.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                    raise ValueError("模拟数据完整性检查失败")
            temporary.replace(path)
            metadata = {"specification": spec, "rows": sum(counts.values()), "rows_by_metric": counts,
                        "database_sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
            pending = manifest.with_suffix(".tmp")
            pending.write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n")
            pending.replace(manifest)
        finally:
            temporary.unlink(missing_ok=True)
    return {**metadata, "database": str(path.resolve()), "manifest": str(manifest.resolve())}


def read_rows(store, sql, parameters):
    # 真正只读；connect 的上下文管理器只管理事务，closing 才会关闭连接。
    with closing(sqlite3.connect(Path(store["database"]).as_uri() + "?mode=ro", uri=True)) as db:
        db.row_factory = sqlite3.Row
        return [dict(r) for r in db.execute(sql, parameters)]
