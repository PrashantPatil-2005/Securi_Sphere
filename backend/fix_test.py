#!/usr/bin/env python3
import re

with open('tests/integration/test_e2e_live_pipeline.py', 'r') as f:
    content = f.read()

# Fix 1: Replace CorrelationRule.rule_type filter with rule_type_from_description
old1 = """    # Confirm the seeded rule exists
        seq_rules = (
            await db.execute(
                select(CorrelationRule).where(
                    CorrelationRule.rule_type == "sequence",
                    CorrelationRule.enabled.is_(True),
                )
            )
        ).scalars().all()
        assert len(seq_rules) >= 1, "seed_correlation_rules did not create sequence rules" """

new1 = """    # Confirm the seeded rule exists (rule type is in description, not a column)
        from app.services.correlation_engine import rule_type_from_description
        all_rules = (
            await db.execute(select(CorrelationRule).where(CorrelationRule.enabled.is_(True)))
        ).scalars().all()
        seq_rules = [r for r in all_rules if rule_type_from_description(r.description) == "sequence"]
        assert len(seq_rules) >= 1, "seed_correlation_rules did not create sequence rules" """

if old1 in content:
    content = content.replace(old1, new1)
    print("Fix 1 applied")
else:
    print("Fix 1 pattern not found")

# Fix 2: Replace the all_results section
old2 = """        all_results = (
            await db.execute(select(CorrelationResult).where(CorrelationResult.host_id == UUID(host_id)))
        ).scalars().all()
        for r in all_results:
            assert r.rule_id is not None
            assert r.event_ids is not None"""

new2 = """        all_results = (
            await db.execute(select(CorrelationResult).where(CorrelationResult.host_id == UUID(host_id)))
        ).scalars().all()
        for r in all_results:
            # rule_id references CorrelationRule; verify it exists
            rule = await db.get(CorrelationRule, r.rule_id)
            assert rule is not None
            assert r.event_ids is not None"""

if old2 in content:
    content = content.replace(old2, new2)
    print("Fix 2 applied")
else:
    print("Fix 2 pattern not found - showing context")
    lines = content.split('\n')
    for i in range(298, 315):
        print(f'{i+1}: {lines[i]}')

with open('tests/integration/test_e2e_live_pipeline.py', 'w') as f:
    f.write(content)