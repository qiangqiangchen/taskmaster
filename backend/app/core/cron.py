"""
轻量级 Cron 表达式解析器
- 支持 5 字段：分 时 日 月 周
- 支持：* / - , 及组合
- 计算下次执行时间
"""
from datetime import datetime, timedelta, timezone


def parse_field(field_str: str, min_val: int, max_val: int) -> set[int]:
    """解析单个 cron 字段，返回合法值集合"""
    values = set()
    for part in field_str.split(","):
        if "/" in part:
            range_part, step_str = part.split("/", 1)
            step = int(step_str)
        else:
            range_part = part
            step = 1

        if range_part == "*":
            start, end = min_val, max_val
        elif "-" in range_part:
            start_str, end_str = range_part.split("-", 1)
            start, end = int(start_str), int(end_str)
        else:
            start = end = int(range_part)

        for v in range(start, end + 1, step):
            values.add(v)

    return values


def parse_cron(expression: str) -> dict[str, set[int]]:
    """解析 5 字段 cron 表达式"""
    fields = expression.strip().split()
    if len(fields) != 5:
        raise ValueError(f"cron 表达式需要 5 个字段，当前 {len(fields)} 个: {expression}")

    return {
        "minute": parse_field(fields[0], 0, 59),
        "hour": parse_field(fields[1], 0, 23),
        "day": parse_field(fields[2], 1, 31),
        "month": parse_field(fields[3], 1, 12),
        "weekday": parse_field(fields[4], 0, 6),  # 0=周一 6=周日
    }


def next_run(expression: str, from_time: datetime | None = None) -> datetime | None:
    """计算下次执行时间（UTC）"""
    if from_time is None:
        from_time = datetime.now(timezone.utc)
    elif from_time.tzinfo is not None:
        # 转为 UTC 后去掉 tzinfo，便于后续比较
        from_time = from_time.astimezone(timezone.utc).replace(tzinfo=None)

    cron = parse_cron(expression)

    # 从下一分钟开始搜索
    dt = from_time.replace(second=0, microsecond=0) + timedelta(minutes=1)

    max_iter = 4 * 366 * 24 * 60

    for _ in range(max_iter):
        if dt.month not in cron["month"]:
            next_m = _next_greater(cron["month"], dt.month)
            if next_m is not None:
                dt = dt.replace(month=next_m, day=1, hour=0, minute=0)
            else:
                dt = dt.replace(year=dt.year + 1, month=min(cron["month"]), day=1, hour=0, minute=0)
            continue

        if dt.day not in cron["day"] or dt.weekday() not in cron["weekday"]:
            dt += timedelta(days=1)
            dt = dt.replace(hour=0, minute=0)
            continue

        if dt.hour not in cron["hour"]:
            next_h = _next_greater(cron["hour"], dt.hour)
            if next_h is not None:
                dt = dt.replace(hour=next_h, minute=0)
            else:
                dt += timedelta(days=1)
                dt = dt.replace(hour=0, minute=0)
            continue

        if dt.minute not in cron["minute"]:
            next_min = _next_greater(cron["minute"], dt.minute)
            if next_min is not None:
                dt = dt.replace(minute=next_min)
            else:
                dt += timedelta(hours=1)
                dt = dt.replace(minute=0)
            continue

        return dt.replace(tzinfo=timezone.utc)

    return None


def _next_greater(values: set[int], current: int) -> int | None:
    """在 values 中找比 current 大的最小值"""
    candidates = sorted(v for v in values if v > current)
    return candidates[0] if candidates else None


def validate_cron(expression: str) -> tuple[bool, str]:
    """校验 cron 表达式，返回 (是否合法, 错误信息)"""
    try:
        fields = expression.strip().split()
        if len(fields) != 5:
            return False, f"需要 5 个字段，当前 {len(fields)} 个"

        ranges = [(0, 59), (0, 23), (1, 31), (1, 12), (0, 6)]
        names = ["分", "时", "日", "月", "周"]
        for i, (field, (lo, hi)) in enumerate(zip(fields, ranges)):
            try:
                parse_field(field, lo, hi)
            except Exception as e:
                return False, f"{names[i]}字段错误: {e}"

        result = next_run(expression)
        if result is None:
            return False, "无法计算出下次执行时间"

        return True, ""
    except Exception as e:
        return False, str(e)


# ========== 预设 ==========

CRON_PRESETS = {
    "每分钟": "* * * * *",
    "每 5 分钟": "*/5 * * * *",
    "每 15 分钟": "*/15 * * * *",
    "每 30 分钟": "*/30 * * * *",
    "每小时": "0 * * * *",
    "每 6 小时": "0 */6 * * *",
    "每天 0 点": "0 0 * * *",
    "每天 8 点": "0 8 * * *",
    "每天 12 点": "0 12 * * *",
    "每周一 9 点": "0 9 * * 0",
    "工作日 9 点": "0 9 * * 0-4",
    "每月 1 号 0 点": "0 0 1 * *",
}