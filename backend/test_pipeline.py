import sys
import os

# Add backend to path
backend_path = r'C:\Users\Prash\Desktop\Securi\backend'
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timedelta, timezone
import asyncio

# Use a simple SQLite setup
engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Import after engine creation so models can register
from app.models.event import Event
from app.models.host import Host
from app.models.alert import Alert
from app.models.siem import Offense

from app.services.mitre import seed_mitre, enrich_event
from app.services.detection import seed_alert_rules, run_detection_for_host
from app.services.offense_engine import link_alert_to_offense, link_event_to_offense, process_new_alert
from app.services.correlation_engine import run_correlation_engine, seed_correlation_rules
from app.services.timeline import build_timelines

async def test_pipeline():
    # Create tables
    from app.database import Base
    Base.metadata.create_all(bind=engine)
    print("OK Tables created")
    
    db = SessionLocal()
    
    # Seed MITRE
    await seed_mitre(db)
    print("OK MITRE seeded")
    
    # Seed alert rules
    await seed_alert_rules(db)
    print("OK Alert rules seeded")
    
    # Seed correlation rules
    await seed_correlation_rules(db)
    print("OK Correlation rules seeded")
    
    # Create a test host
    host = Host(
        id="host-001",
        name="web-01",
        api_key_hash="test_hash",
        status="online",
        last_seen=None
    )
    db.add(host)
    db.commit()
    db.refresh(host)
    print(f"OK Created host: {host.name} ({host.id})")
    
    # Simulate the attack: 12 failed logins + 1 success + sudo
    now = datetime.now(timezone.utc)
    
    events = []
    
    # 12 failed logins from 192.168.1.100
    for i in range(12):
        events.append(Event(
            id=f"event-{i}",
            host_id=host.id,
            event_type="ssh_login_failure",
            severity="medium",
            description="SSH login failure",
            source_ip="192.168.1.100",
            username="admin",
            raw_log=f"Feb 10 10:00:00 server sshd[1234]: Failed password for admin from 192.168.1.100 port 52752 ssh2",
            timestamp=now - timedelta(minutes=12 + i*1)
        ))
    
    # 1 successful login
    events.append(Event(
        id="event-12",
        host_id=host.id,
        event_type="ssh_login_success",
        severity="low",
        description="SSH login success for admin",
        source_ip="192.168.1.100",
        username="admin",
        raw_log="Feb 10 10:12:00 server sshd[1235]: Accepted password for admin from 192.168.1.100 port 52752 ssh2",
        timestamp=now - timedelta(minutes=1)
    ))
    
    # 1 sudo usage
    events.append(Event(
        id="event-13",
        host_id=host.id,
        event_type="sudo_usage",
        severity="low",
        description="Sudo used by admin",
        source_ip="192.168.1.100",
        username="admin",
        raw_log="Feb 10 10:13:00 server sudo: pam_unix(sudo: session opened for admin by admin)",
        timestamp=now
    ))
    
    # Add events to DB
    for e in events:
        db.add(e)
    db.commit()
    print(f"OK Added {len(events)} events")
    
    # Enrich events with MITRE
    for e in events:
        enrich_event(e)
    db.commit()
    print("OK Events enriched with MITRE")
    
    # Run detection
    await run_detection_for_host(db, host)
    print("OK Detection run")
    
    # Run correlation
    results = await run_correlation_engine(db, host.id)
    print(f"OK Correlation found {len(results)} results")
    for r in results:
        print(f"  - rule={r.rule_id}: confidence={r.confidence:.2f}")
    
    # Check alerts
    stmt = select(Alert)
    alerts = db.execute(stmt).scalars().all()
    print(f"OK Total alerts: {len(alerts)}")
    for a in alerts:
        print(f"  - {a.title} (severity={a.severity}, mitre={a.mitre_technique_id}/{a.mitre_tactic})")
    
    # Check offenses
    stmt = select(Offense)
    offenses = db.execute(stmt).scalars().all()
    print(f"OK Total offenses: {len(offenses)}")
    for o in offenses:
        print(f"  - Offense #{o.offense_number}: {o.title} risk={o.risk_level} events={o.event_count} alerts={o.alert_count}")
        if o.timeline:
            print(f"    timeline entries: {len(o.timeline)}")
    
    # Build timelines
    timelines = await build_timelines(db, host.id)
    print(f"OK Timelines built: {len(timelines)}")
    for t in timelines:
        print(f"  - {t.title} severity={t.severity} confidence={t.confidence:.1f}")
    
    db.close()
    
    print("\n=== PHASE 0 VERIFICATION ===")
    print("If you can see alerts, offenses, and timelines above, the pipeline works!")
    print("The jury story: T1110 (brute force) -> T1078 (success) -> T1548 (sudo escalation)")

asyncio.run(test_pipeline())