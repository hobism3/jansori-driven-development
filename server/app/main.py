"""App factory + loopback-only entry point (SPEC 5, US-15).

SUPPORTED entrypoint (loopback enforced before serving):
    python -m server.app.main

Bind host/port come from JANSORI_HOST (default 127.0.0.1) / JANSORI_PORT (default 8765).
`assert_loopback` refuses to start if a non-loopback host is configured.

Defense-in-depth: a FastAPI startup guard also re-asserts JANSORI_HOST is loopback, so
serving via `uvicorn server.app.main:app` (which reads JANSORI_HOST) is still guarded.
NOTE: passing an explicit `uvicorn --host <routable>` on the CLI bypasses env config and
cannot be intercepted from inside the app — do NOT use that form; use the module
entrypoint above (and U4's `make run`, which uses it).
"""
from __future__ import annotations

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI

from ..domain.errors import DomainError
from ..security.guard import assert_loopback
from .errors import domain_error_handler, unhandled_error_handler
from .routes import Container, register_routes


def configured_host() -> str:
    return os.environ.get("JANSORI_HOST", "127.0.0.1")


@asynccontextmanager
async def _lifespan(app: FastAPI):
    # SPEC 5: re-assert loopback on every serving path that honors JANSORI_HOST.
    assert_loopback(configured_host())
    yield


def create_app(container: Container | None = None) -> FastAPI:
    app = FastAPI(
        title="Jansori U1 — Capsule Server",
        description="Loopback-only Capsule store & SPEC 8 contracts. "
        "'/normalize' = Capsule Normalization (SPEC compaction), NOT Claude Code context compaction.",
        version="0.1.0",
        lifespan=_lifespan,
    )
    register_routes(app, container or Container.build())
    app.add_exception_handler(DomainError, domain_error_handler)
    app.add_exception_handler(Exception, unhandled_error_handler)
    return app


app = create_app()


def main() -> None:
    import uvicorn

    host = configured_host()
    port = int(os.environ.get("JANSORI_PORT", "8765"))
    assert_loopback(host)  # SPEC 5: refuse non-loopback bind before serving
    uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    main()
