from __future__ import annotations

import logging
from celery import shared_task
from sqlmodel import Session

from ..db import engine
from ..models import AuditLog
from ..agent.orchestrator import Orchestrator

logger = logging.getLogger("tasks.jobs")
from __future__ import annotations

from celery import shared_task
from ..tasks.facebook_auto import facebook_autoreply_tick


@shared_task(name="app.tasks.jobs.facebook_autoreply_tick")
def facebook_autoreply_tick_job():
    return facebook_autoreply_tick()



def _run_command(text: str) -> dict:
    with Session(engine) as session:
        orch = Orchestrator(session=session)
        res = orch.handle_command(text)
        return res.model_dump()


@shared_task(name="app.tasks.jobs.nightly_inbox_triage")
def nightly_inbox_triage():
    out = _run_command("Triage inbox")
    with Session(engine) as session:
        session.add(AuditLog(event_type="system", message="nightly_inbox_triage", payload=out))
        session.commit()
    return out


@shared_task(name="app.tasks.jobs.nightly_product_research")
def nightly_product_research():
    out = _run_command("Add a winning product and prepare it to sell")
    with Session(engine) as session:
        session.add(AuditLog(event_type="system", message="nightly_product_research", payload=out))
        session.commit()
    return out


@shared_task(name="app.tasks.jobs.nightly_content_generation")
def nightly_content_generation():
    out = _run_command("Generate 7 posts and queue for approval")
    with Session(engine) as session:
        session.add(AuditLog(event_type="system", message="nightly_content_generation", payload=out))
        session.commit()
    return out


@shared_task(name="app.tasks.jobs.daily_report")
def daily_report():
    out = _run_command("Show me system status")
    with Session(engine) as session:
        session.add(AuditLog(event_type="system", message="daily_report", payload=out))
        session.commit()
    return out
