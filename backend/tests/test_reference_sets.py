"""Tests for reference set SIEM expansion."""

import pytest

from app.services.reference_sets import is_ref_filter, ref_set_name, resolve_ref_filters
from app.services.siem_search import parse_siem_query


def test_ref_filter_detection():
    assert is_ref_filter("ref:bad_ips")
    assert ref_set_name("ref:bad_ips") == "bad_ips"
    assert not is_ref_filter("1.2.3.4")


@pytest.mark.asyncio
async def test_resolve_ref_filters_expands(prepare_database):
    from app.database import async_session
    from app.models.reference import ReferenceSet, ReferenceSetEntry

    async with async_session() as db:
        rs = ReferenceSet(name="test_ips", set_type="ip", description="test")
        db.add(rs)
        await db.flush()
        db.add(ReferenceSetEntry(set_id=rs.id, value="10.0.0.1"))
        await db.flush()

        parsed = parse_siem_query("source_ip:ref:test_ips severity:high")
        resolved = await resolve_ref_filters(db, parsed)
        assert "source_ip" not in resolved["filters"]
        assert resolved["in_filters"]["source_ip"] == ["10.0.0.1"]
