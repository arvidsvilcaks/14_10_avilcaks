"""Ezermalas CRM lietotne.

Palaišana: make run (uvicorn crm.app:app --reload)
"""

import os
import secrets
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from crm import auth, db, kludas, lomas, mijiedarbibas, organizacijas, panelis
from crm.sabloni import veidnes

SESIJAS_ILGUMS = 8 * 60 * 60


def _sesijas_atslega() -> str:
    # Bez CRM_SESSION_SECRET sesijas derīgas tikai līdz servera restartam.
    return os.environ.get("CRM_SESSION_SECRET") or secrets.token_urlsafe(32)


@asynccontextmanager
async def _dzive(app: FastAPI) -> AsyncIterator[None]:
    db.inicializet()
    yield


def izveidot_lietotni() -> FastAPI:
    app = FastAPI(title="Ezermalas CRM", version="0.2.0", lifespan=_dzive)
    app.add_middleware(
        SessionMiddleware,
        secret_key=_sesijas_atslega(),
        session_cookie="crm_sesija",
        max_age=SESIJAS_ILGUMS,
        same_site="lax",
        https_only=os.environ.get("CRM_HTTPS") == "1",
    )
    app.mount("/static", StaticFiles(directory=db.SAKNE / "static"), name="static")
    kludas.registret(app)
    app.include_router(auth.router)
    app.include_router(lomas.router)
    app.include_router(organizacijas.router)
    app.include_router(mijiedarbibas.router)
    app.include_router(panelis.router)
    veidnes.env.globals["macibu_rezims"] = lomas.macibu_rezims
    veidnes.env.globals["lomu_nosaukumi"] = auth.LOMU_NOSAUKUMI
    return app


app = izveidot_lietotni()
