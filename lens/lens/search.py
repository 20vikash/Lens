from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import Any

FIELDS = ("resource_id", "product", "service", "level", "source")
COLUMNS = (*FIELDS, "message")
LEVELS = ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")
LEVEL_ALIASES = {"WARN": "WARNING", "ERR": "ERROR", "FATAL": "CRITICAL", "TRACE": "DEBUG"}
OPERATORS = ("eq", "ne", "gt", "lt", "gte", "lte", "contains")
NUMERIC_OPS = ("gt", "lt", "gte", "lte")
_ATTR_KEY = re.compile(r"^[A-Za-z0-9_.:-]+$")


def _normalize_level(raw: str) -> str:
	"""Map producer-level names (warn, err, …) to the canonical set the UI expects."""
	upper = str(raw or "").upper()
	return LEVEL_ALIASES.get(upper, upper)


def _column_for(field: str) -> str | None:
	"""The SQL expression for a field, or None if the field is invalid."""
	if field in COLUMNS:
		return field
	if field.startswith("attr."):
		key = field[5:]
		if _ATTR_KEY.match(key):
			return f"attributes[{key!r}]"
	return None


def _condition_clause(field: str, op: str, value: Any, idx: int) -> tuple[str, Any] | None:
	"""One WHERE fragment plus its bound parameter, or None if it cannot be built."""
	if op not in OPERATORS:
		return None
	column = _column_for(field)
	if column is None:
		return None
	name = f"c{idx}"
	raw = "" if value is None else str(value)
	if not raw and op != "eq":
		return None

	is_attr_numeric = field.startswith("attr.") and op in NUMERIC_OPS
	if is_attr_numeric:
		try:
			number = float(raw)
		except ValueError:
			return None
		symbol = {"gt": ">", "lt": "<", "gte": ">=", "lte": "<="}[op]
		return (f"toFloat64OrDefault({column}) {symbol} {{{name}:Float64}}", number)
	if op == "contains":
		return (f"positionCaseInsensitive({column}, {{{name}:String}}) > 0", raw)
	symbol = {"eq": "=", "ne": "!=", "gt": ">", "lt": "<", "gte": ">=", "lte": "<="}[op]
	return (f"{column} {symbol} {{{name}:String}}", raw)


def build_filters(
	start: int,
	end: int,
	query: str = "",
	levels: list[str] | None = None,
	filters: dict[str, list[str]] | None = None,
	conditions: list[dict] | None = None,
) -> tuple[str, dict]:
	parameters: dict[str, Any] = {"start": start, "end": end}
	clauses = [
		"ts >= fromUnixTimestamp64Milli({start:Int64})",
		"ts <= fromUnixTimestamp64Milli({end:Int64})",
	]

	if query:
		query = query.strip()
		if query:
			parameters["q"] = query
			clauses.append(
				"(positionCaseInsensitive(message, {q:String}) > 0"
				" OR arrayExists(v -> positionCaseInsensitive(v, {q:String}) > 0, mapValues(attributes)))"
			)

	if levels:
		match = [lv for lv in levels if lv in LEVELS]
		for alias, canonical in LEVEL_ALIASES.items():
			if canonical in match and alias not in match:
				match.append(alias)
		if match:
			parameters["levels"] = match
			clauses.append("upper(level) IN {levels:Array(LowCardinality(String))}")

	for field in FIELDS:
		values = (filters or {}).get(field) or []
		values = [v for v in values if v]
		if values:
			parameters[field] = values
			clauses.append(f"{field} IN {{{field}:Array(LowCardinality(String))}}")

	cond_parts: list[str] = []
	for idx, cond in enumerate(conditions or []):
		built = _condition_clause(cond.get("field", ""), cond.get("op", ""), cond.get("value"), idx)
		if not built:
			continue
		clause, value = built
		parameters[f"c{idx}"] = value
		conjunction = cond.get("conjunction", "and")
		if not cond_parts:
			cond_parts.append(f"({clause})")
		else:
			joiner = " OR " if conjunction == "or" else " AND "
			cond_parts.append(f"{joiner}({clause})")
	if cond_parts:
		clauses.append("(" + "".join(cond_parts) + ")")

	return " AND ".join(clauses), parameters


def bucket_seconds(start_ms: int, end_ms: int, target_buckets: int = 60) -> int:
	span = max((end_ms - start_ms) / 1000, 1)
	return max(int(span / target_buckets), 1)


STATS_FIELDS = ("resource_id", "product", "service", "level")
SECONDS_PER_DAY = 86_400


def _stats_histogram(
	client: Any,
	start: int,
	end: int,
	levels: list[str] | None,
	filters: dict[str, list[str]] | None,
) -> dict:
	"""Daily histogram from the pre-aggregated `daily_log_stats` table.

	Returns ``{bucket_ms: {level: count}}`` keyed at UTC midnight. Returns an
	empty dict if the table is unavailable so the caller can fall back.
	"""
	start_date = datetime.fromtimestamp(start / 1000, tz=UTC).date()
	end_date = datetime.fromtimestamp(end / 1000, tz=UTC).date()
	parameters: dict[str, Any] = {"start_date": start_date, "end_date": end_date}
	clauses = ["date >= {start_date:Date}", "date <= {end_date:Date}"]

	if levels:
		valid = [lv for lv in levels if lv in LEVELS]
		for alias, canonical in LEVEL_ALIASES.items():
			if canonical in valid and alias not in valid:
				valid.append(alias)
		if valid:
			parameters["levels"] = valid
			clauses.append("upper(level) IN {levels:Array(LowCardinality(String))}")

	for field in ("resource_id", "product", "service"):
		values = [v for v in (filters or {}).get(field, []) if v]
		if values:
			parameters[field] = values
			clauses.append(f"{field} IN {{{field}:Array(LowCardinality(String))}}")

	try:
		response = client.query(
			"SELECT date, level, sum(log_count) AS count"
			f" FROM daily_log_stats WHERE {' AND '.join(clauses)}"
			" GROUP BY date, level ORDER BY date",
			parameters=parameters,
		)
	except Exception:
		return {}

	histogram: dict[int, dict[str, int]] = {}
	for d, lvl, count in response.result_rows:
		key = int(datetime.combine(d, datetime.min.time(), tzinfo=UTC).timestamp() * 1000)
		histogram.setdefault(key, {})[_normalize_level(lvl)] = count
	return histogram


def _can_use_stats_table(
	span_seconds: int,
	query: str,
	filters: dict[str, list[str]] | None,
	conditions: list[dict] | None,
) -> bool:
	"""The stats table only carries daily buckets and a subset of fields, so
	it can only stand in for the histogram when no message/source/attribute
	filtering is required and the range is wide enough for daily buckets."""
	if span_seconds <= SECONDS_PER_DAY:
		return False
	if query and query.strip():
		return False
	if (filters or {}).get("source"):
		return False
	if conditions:
		return False
	return True


def search(
	client: Any,
	start: int,
	end: int,
	query: str = "",
	levels: list[str] | None = None,
	filters: dict[str, list[str]] | None = None,
	conditions: list[dict] | None = None,
	limit: int = 100,
	offset: int = 0,
	order: str = "desc",
) -> dict:
	where, parameters = build_filters(start, end, query, levels, filters, conditions)
	base = f"FROM logs WHERE {where}"

	total = client.query(f"SELECT count() {base}", parameters=parameters).result_rows[0][0]
	order_dir = "ASC" if order == "asc" else "DESC"
	parameters.update({"limit": min(limit, 500), "offset": offset})
	rows_result = client.query(
		f"SELECT ts, resource_id, product, service, level, source, message, attributes {base}"
		f" ORDER BY ts {order_dir} LIMIT {{limit:Int32}} OFFSET {{offset:Int32}}",
		parameters=parameters,
	)
	rows = []
	columns = rows_result.column_names
	for raw in rows_result.result_rows:
		row = dict(zip(columns, raw, strict=True))
		row["ts"] = int(row["ts"].timestamp() * 1000)
		row["attributes"] = row.get("attributes") or {}
		row["level"] = _normalize_level(row.get("level"))
		rows.append(row)

	span = max((end - start) / 1000, 1)
	bucket = bucket_seconds(start, end)
	histogram: dict[int, dict[str, int]] = {}

	if _can_use_stats_table(span, query, filters, conditions):
		stats = _stats_histogram(client, start, end, levels, filters)
		if stats:
			bucket = SECONDS_PER_DAY
			histogram = stats

	if not histogram:
		parameters["bucket"] = bucket
		histogram_result = client.query(
			f"SELECT toStartOfInterval(ts, INTERVAL {{bucket:Int32}} SECOND) AS bucket,"
			f" level, count() AS count {base} GROUP BY bucket, level ORDER BY bucket",
			parameters=parameters,
		)
		for b_ts, lvl, count in histogram_result.result_rows:
			key = int(b_ts.timestamp() * 1000)
			histogram.setdefault(key, {})[_normalize_level(lvl)] = count

	facets = get_facets(client, base, parameters)
	facets["__attributes__"] = get_attribute_facets(client, base, parameters)
	return {
		"total": total,
		"rows": rows,
		"histogram": [{"bucket": key, "counts": histogram[key]} for key in sorted(histogram)],
		"facets": facets,
		"bucket_seconds": bucket,
	}


def get_facets(client: Any, base: str, parameters: dict) -> dict:
	result = {}
	for field in FIELDS:
		try:
			value_expr = f"upper({field})" if field == "level" else field
			response = client.query(
				f"SELECT {value_expr} AS value, count() AS count {base}"
				f" GROUP BY value ORDER BY count DESC LIMIT 10",
				parameters=parameters,
			)
			result[field] = [
				{
					"value": _normalize_level(value)
					if field == "level"
					else (str(value) if value is not None else ""),
					"count": count,
				}
				for value, count in response.result_rows
			]
		except Exception:
			result[field] = []
	return result


def get_attribute_facets(client: Any, base: str, parameters: dict) -> dict:
	"""Top attribute keys, each with its top values. One query for the keys,
	then one per key — attributes are sparse, so a single unpivot is slower."""
	try:
		key_rows = client.query(
			f"SELECT k AS key, count() AS count {base.replace('FROM logs WHERE', 'FROM logs ARRAY JOIN mapKeys(attributes) AS k WHERE')} GROUP BY k ORDER BY count DESC LIMIT 8",
			parameters=parameters,
		).result_rows
	except Exception:
		key_rows = []
	result = []
	for key, count in key_rows:
		if not isinstance(key, str) or not _ATTR_KEY.match(key):
			continue
		entry = {"key": key, "count": count, "values": []}
		try:
			value_rows = client.query(
				f"SELECT attributes[{key!r}] AS value, count() AS count {base}"
				f" AND has(mapKeys(attributes), {key!r}) GROUP BY value ORDER BY count DESC LIMIT 5",
				parameters=parameters,
			).result_rows
			entry["values"] = [{"value": str(v) if v is not None else "", "count": c} for v, c in value_rows]
		except Exception:
			pass
		result.append(entry)
	return result
