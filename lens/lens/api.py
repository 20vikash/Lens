from __future__ import annotations

from typing import Any

import frappe

from .clickhouse import get_client, list_sources
from .search import LEVELS, OPERATORS
from .search import search as run_search


@frappe.whitelist()
def get_sources() -> dict:
	return {"sources": list_sources(), "levels": list(LEVELS), "operators": list(OPERATORS)}


@frappe.whitelist(methods=["POST"])
def search_logs(
	start: int,
	end: int,
	source: str | None = None,
	query: str = "",
	levels: str | list | None = None,
	filters: str | dict | None = None,
	conditions: str | list | None = None,
	limit: int = 100,
	offset: int = 0,
	order: str = "desc",
) -> dict:
	client = get_client(source)
	return run_search(
		client,
		int(start),
		int(end),
		query=str(query or ""),
		levels=_as_list(levels),
		filters=_as_dict(filters),
		conditions=_as_conditions(conditions),
		limit=int(limit or 100),
		offset=int(offset or 0),
		order=order,
	)


def _as_list(value: Any) -> list:
	if not value:
		return []
	if isinstance(value, str):
		import json

		try:
			value = json.loads(value)
		except ValueError:
			value = [v for v in value.split(",") if v]
	return [str(v) for v in value]


def _as_dict(value: Any) -> dict:
	if not value:
		return {}
	if isinstance(value, str):
		import json

		value = json.loads(value)
	return {key: _as_list(val) for key, val in (value or {}).items()}


def _as_conditions(value: Any) -> list[dict]:
	if not value:
		return []
	if isinstance(value, str):
		import json

		value = json.loads(value)
	if not isinstance(value, list):
		return []
	out = []
	for item in value:
		if not isinstance(item, dict):
			continue
		field = str(item.get("field") or "")
		op = str(item.get("op") or "")
		if field and op in OPERATORS:
			cond = {"field": field, "op": op, "value": item.get("value", "")}
			if str(item.get("conjunction") or "and") == "or":
				cond["conjunction"] = "or"
			out.append(cond)
	return out
