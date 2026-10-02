"""独立的模拟物理数据：不读取案例或评分标准。

商户、订单汇总桶、加入事件分别存表，避免以一个粒度解释所有指标。
日期/筛选由上游任务给出；比率先加总分子分母，绝不平均行比率。
"""
import itertools
import sqlite3

DATA_VERSION = 'synthetic-query-v2'
SPECS = {
    'lab_fx_gross_premium': ('facts', 'SUM(premium)'),
    'lab_fx_net_premium': ('facts', 'SUM(premium - refund)'),
    'lab_active_merchants': ('facts', 'COUNT(DISTINCT merchant_id)'),
    'lab_active_fx_open': ('facts', 'COUNT(DISTINCT merchant_id)'),
    'lab_takeaway_orders': ('orders', 'SUM(order_count)'),
    'lab_join_funnel': ('join_events', 'COUNT(DISTINCT merchant_id)'),
    'lab_fx_order_rate': ('orders', '100.0 * SUM(CASE WHEN fx_insured = 1 AND order_status = \'non_cancelled\' THEN order_count ELSE 0 END) / NULLIF(SUM(CASE WHEN order_status = \'non_cancelled\' THEN order_count ELSE 0 END), 0)'),
    'lab_fx_eligible_rate': ('orders', '100.0 * SUM(CASE WHEN fx_insured = 1 THEN order_count ELSE 0 END) / NULLIF(SUM(CASE WHEN eligible = 1 THEN order_count ELSE 0 END), 0)'),
    'lab_cancel_order_rate': ('orders', '100.0 * SUM(CASE WHEN cancel_insured = 1 THEN order_count ELSE 0 END) / NULLIF(SUM(order_count), 0)'),
}
TABLE_COLUMNS = {
    'facts': {'province', 'delivery', 'city_operation', 'city_tier', 'merchant_age'},
    'orders': {'province', 'merchant_age', 'merchant_type', 'category_l1', 'order_status'},
    'join_events': {'insurance_type', 'channel_l1', 'source'},
}


def seed_database(path):
    """全因子枚举生成，和测试问法无关。旧批次数据库不迁移、不覆盖。"""
    with sqlite3.connect(path) as db:
        exists = db.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        if exists:
            if ('metadata',) not in exists or db.execute('SELECT version FROM metadata').fetchone()[0] != DATA_VERSION:
                raise ValueError('模拟数据版本已改变，必须新建批次，不能覆写旧数据')
            return
        db.execute('CREATE TABLE metadata (version TEXT)')
        db.execute('INSERT INTO metadata VALUES (?)', (DATA_VERSION,))
        db.execute('''CREATE TABLE facts (merchant_id TEXT, day TEXT, province TEXT,
            delivery TEXT, city_operation TEXT, city_tier TEXT, merchant_age TEXT,
            valid INTEGER, fx_open INTEGER, premium INTEGER, refund INTEGER)''')
        axes = ((7, 8), ('anhui', 'jiangsu', 'shanghai'), ('dedicated', 'crowd', 'self'),
                ('direct', 'agency'), ('tier1', 'tier2', 'tier3', 'tier4', 'tier5'),
                ('new', 'old'), (0, 1), (0, 1))
        rows = []
        for i, (month, province, delivery, op, tier, age, valid, opened) in enumerate(itertools.product(*axes)):
            # 8月多一倍商户，使查错月份也更容易在数值中发现；仍必须检查任务范围。
            for j in range(1 if month == 7 else 2):
                rows.append((f'm-{i}-{j}', f'2026-{month:02}-15', province, delivery,
                             op, tier, age, valid, opened, 100+i*3, 10+i%7))
        db.executemany('INSERT INTO facts VALUES (?,?,?,?,?,?,?,?,?,?,?)', rows)
        db.execute('''CREATE TABLE orders (day TEXT, province TEXT, merchant_age TEXT,
            merchant_type TEXT, category_l1 TEXT, order_status TEXT,
            eligible INTEGER, fx_insured INTEGER, cancel_insured INTEGER, order_count INTEGER)''')
        rows = []
        axes = ((7, 8), ('anhui', 'jiangsu', 'shanghai'), ('new', 'old'),
                ('ka', 'cka', 'city'), ('food', 'entertainment', 'service'),
                ('non_cancelled', 'cancelled'), (0, 1), (0, 1), (0, 1))
        for i, row in enumerate(itertools.product(*axes)):
            month, province, age, merchant_type, category, status, eligible, insured, cancelled = row
            if insured and not eligible:
                continue  # 投保订单必须属于可投保总体。
            rows.append((f'2026-{month:02}-15', province, age, merchant_type, category,
                         status, eligible, insured, cancelled, (i%7+1)*(1 if month == 7 else 2)))
        db.executemany('INSERT INTO orders VALUES (?,?,?,?,?,?,?,?,?,?)', rows)
        db.execute('''CREATE TABLE join_events (merchant_id TEXT, day TEXT,
            insurance_type TEXT, channel_l1 TEXT, source TEXT)''')
        rows = []
        axes = ((7, 8), ('fx', 'qsb', 'cancel'), ('wallet', 'open', 'outreach'),
                ('app', 'telesales', 'organic'))
        for i, (month, insurance, channel, source) in enumerate(itertools.product(*axes)):
            for j in range((i%3+1)*(1 if month == 7 else 2)):
                # 一个商户可以多次触发事件，查询必须去重。
                event = (f'j-{i}-{j}', f'2026-{month:02}-15', insurance, channel, source)
                rows.extend([event, event])
        db.executemany('INSERT INTO join_events VALUES (?,?,?,?,?)', rows)
