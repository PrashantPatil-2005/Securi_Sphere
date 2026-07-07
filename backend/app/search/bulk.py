"""Bulk indexing helpers for OpenSearch."""

from __future__ import annotations

from typing import Any, Iterable


def chunk_iterable(items: list, size: int) -> Iterable[list]:
    for i in range(0, len(items), size):
        yield items[i : i + size]


def build_bulk_actions(index: str, docs: list[tuple[str, dict[str, Any]]]) -> list[dict[str, Any]]:
    actions: list[dict[str, Any]] = []
    for doc_id, body in docs:
        actions.append({"index": {"_index": index, "_id": doc_id}})
        actions.append(body)
    return actions
