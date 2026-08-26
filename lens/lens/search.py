from __future__ import annotations

import re
from typing import Any

FIELDS = ("resource_id", "product", "service", "level", "source")
COLUMNS = (*FIELDS, "message")
LEVELS = ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")
OPERATORS = ("eq", "ne", "gt", "lt", "gte", "lte", "contains")
NUMERIC_OPS = ("gt", "lt", "gte", "lte")
_ATTR_KEY = re.compile(r"^[A-Za-z0-9_.:-]+$")


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
		parameters["levels"] = [lv for lv in levels if lv in LEVELS]
		if parameters["levels"]:
			clauses.append("level IN {levels:Array(LowCardinality(String))}")

	for field in FIELDS:
		values = (filters or {}).get(field) or []
		values = [v for v in values if v]
		if values:
			parameters[field] = values
			clauses.append(f"{field} IN {{{field}:Array(LowCardinality(String))}}")

	for idx, cond in enumerate(conditions or []):
		built = _condition_clause(cond.get("field", ""), cond.get("op", ""), cond.get("value"), idx)
		if not built:
			continue
		clause, value = built
		clauses.append(clause)
		parameters[f"c{idx}"] = value

	return " AND ".join(clauses), parameters


def bucket_seconds(start_ms: int, end_ms: int, target_buckets: int = 60) -> int:
	span = max((end_ms - start_ms) / 1000, 1)
	return max(int(span / target_buckets), 1)


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
		rows.append(row)

	bucket = bucket_seconds(start, end)
	parameters["bucket"] = bucket
	histogram_result = client.query(
		f"SELECT toStartOfInterval(ts, INTERVAL {{bucket:Int32}} SECOND) AS bucket,"
		f" level, count() AS count {base} GROUP BY bucket, level ORDER BY bucket",
		parameters=parameters,
	)
	histogram = {}
	for b_ts, lvl, count in histogram_result.result_rows:
		key = int(b_ts.timestamp() * 1000)
		histogram.setdefault(key, {})[lvl] = count

	facets = get_facets(client, base, parameters)
	facets["__attributes__"] = get_attribute_facets(client, base, parameters)
	return {
		"total": total,
		"rows": rows,
		"histogram": [
			{"bucket": key, "counts": histogram[key]} for key in sorted(histogram)
		],
		"facets": facets,
		"bucket_seconds": bucket,
	}


def get_facets(client: Any, base: str, parameters: dict) -> dict:
	result = {}
	for field in FIELDS:
		try:
			response = client.query(
				f"SELECT {field} AS value, count() AS count {base}"
				f" GROUP BY value ORDER BY count DESC LIMIT 10",
				parameters=parameters,
			)
			result[field] = [
				{"value": str(value) if value is not None else "", "count": count}
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
			entry["values"] = [
				{"value": str(v) if v is not None else "", "count": c} for v, c in value_rows
			]
		except Exception:
			pass
		result.append(entry)
	return result
