from __future__ import annotations

from typing import Any

import frappe

DOCTYPE = "Insights Data Source v3"
DATABASE_TYPE = "ClickHouse"


def get_client(source: str | None = None):
    from clickhouse_connect import get_client as ch_get_client

    values = frappe.get_all(
        DOCTYPE,
        filters={"database_type": DATABASE_TYPE},
        fields=["name", "host", "port", "use_ssl", "database_name", "username"],
    )
    if not values:
        frappe.throw(frappe._("No ClickHouse data source found in Insights."))
    name = source or values[0].name
    doc = next((v for v in values if v.name == name), None)
    if not doc:
        frappe.throw(frappe._("Data source {0} not found").format(name))

    password = frappe.get_doc(DOCTYPE, name).get_password(raise_exception=False)
    return ch_get_client(
        host=doc.host,
        port=int(doc.port or 8123),
        username=doc.username,
        password=password,
        database=doc.database_name,
        secure=bool(doc.use_ssl),
        connect_timeout=5,
        query_limit=0,
    )


def list_sources() -> list[str]:
    return frappe.get_all(
        DOCTYPE,
        filters={"database_type": DATABASE_TYPE},
        pluck="name",
    )


def run(client: Any, query: str, parameters: dict | None = None) -> list[dict]:
    response = client.query(query, parameters=parameters or {})
    columns = list(response.column_names)
    return [dict(zip(columns, row, strict=True)) for row in response.result_rows]
