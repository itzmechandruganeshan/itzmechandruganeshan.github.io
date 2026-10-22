"""In-process jobs (single machine): news ingest, Qdrant keepalive, retention purge, email outbox."""

from __future__ import annotations

import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from app.news.ingest import run_ingest
from app.tools import notify, questions

log = logging.getLogger(__name__)


def start_scheduler(rt, memory) -> AsyncIOScheduler:
    d = rt.deps
    s = d.settings
    sched = AsyncIOScheduler(timezone=s.timezone)

    async def news_job():
        log.info("news ingest: %s", await run_ingest(d, rt.http))

    async def keepalive():
        if d.store is not None:
            await d.store.keepalive()

    async def purge():
        # visitors inactive for retention_days are forgotten entirely, checkpoints included
        log.info("purge: forgot %d inactive visitors", await memory.purge())

    async def summarize_idle():
        n = await memory.summarize_idle()
        if n:
            log.info("memory: summarised %d quiet conversations", n)

    async def outbox():
        if d.actions and d.actions.configured():
            await notify.deliver_due(d.db, d.box, s, d.actions)

    sched.add_job(news_job, CronTrigger(hour="6,18", minute=0), id="news", max_instances=1, coalesce=True)
    sched.add_job(keepalive, CronTrigger(hour=4, minute=30), id="keepalive")
    sched.add_job(purge, CronTrigger(hour=3, minute=0), id="purge")
    sched.add_job(outbox, IntervalTrigger(seconds=30), id="outbox", max_instances=1, coalesce=True)
    async def refresh_connections():
        if d.actions and d.actions.s.composio_api_key and not d.actions.configured():
            before = dict(d.actions.connected)
            after = await d.actions.refresh()
            if after != before:
                log.info("composio connections now %s", after)

    async def collect_answers():
        n = await questions.collect(d)
        if n:
            log.info("ask-the-real-me: %d answers collected", n)

    sched.add_job(refresh_connections, IntervalTrigger(minutes=2), id="composio", max_instances=1, coalesce=True)
    sched.add_job(collect_answers, IntervalTrigger(minutes=5), id="answers", max_instances=1, coalesce=True)
    sched.add_job(summarize_idle, IntervalTrigger(minutes=5), id="memory", max_instances=1, coalesce=True)
    sched.start()
    return sched
