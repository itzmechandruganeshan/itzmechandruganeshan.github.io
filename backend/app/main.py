"""FastAPI entry point."""

from __future__ import annotations

import asyncio
import contextlib
import logging

from zoneinfo import ZoneInfo

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from app.chat import TurnRunner
from app.config import get_settings
from app.context.clock import public_status
from app.graph.build import build_graph
from app.jobs.scheduler import start_scheduler
from app.memory import VisitorMemory
from app.retrieval.embed import warm
from app.runtime import build_runtime
from app.ws import router as ws_router

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("virtual-me")


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    s = get_settings()
    rt = await build_runtime(s)
    await asyncio.to_thread(warm)  # load embedding models now, not on the first visitor's message
    s.checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
    async with AsyncSqliteSaver.from_conn_string(str(s.checkpoint_path)) as saver:
        graph = build_graph(saver)
        app.state.runtime = rt
        app.state.runner = TurnRunner(graph, rt.deps)
        app.state.memory = VisitorMemory(rt.deps, graph, saver)
        sched = start_scheduler(rt, app.state.memory)
        log.info("ready: store=%s jev=%s llm=%s", rt.store_backend, s.jev_model, s.llm_models)
        try:
            yield
        finally:
            sched.shutdown(wait=False)
            await rt.close()


app = FastAPI(title="Virtual Me", version="0.1.0", lifespan=lifespan)
app.include_router(ws_router)
# The site's hero reads /status from the browser, so it needs CORS (the websocket checks the origin itself).
app.add_middleware(CORSMiddleware, allow_origins=get_settings().allowed_origins, allow_methods=["GET"])


@app.get("/healthz")
async def healthz():
    return {"ok": True}


@app.get("/status")
async def status():
    rt = app.state.runtime
    now = rt.deps.now().astimezone(ZoneInfo(rt.deps.settings.timezone))
    return {"line": public_status(rt.deps.kb, now)}


@app.get("/readyz")
async def readyz():
    rt = app.state.runtime
    s = rt.deps.settings
    checks = {
        "openrouter_key": bool(s.openrouter_api_key),
        "store": rt.deps.store is not None,
        "store_backend": rt.store_backend,
        "db": True,
        "lead_key": bool(s.lead_key_b64) or not s.is_prod,
    }
    try:
        await rt.deps.db.fetchone("SELECT 1")
    except Exception:  # noqa: BLE001
        checks["db"] = False
    ok = checks["openrouter_key"] and checks["db"] and checks["lead_key"]
    return JSONResponse(checks, status_code=200 if ok else 503)
