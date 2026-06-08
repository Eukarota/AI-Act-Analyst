"""
FastAPI application factory.

Startup wires the AgentDependencies + RunStore (factories.build_wired_app)
and the AssessmentRunner; shutdown closes the LLM client and the Postgres
pool. Routes pull both via Depends so tests can override them.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from backend.api.assess_runner import AssessmentRunner
from backend.api.drift import DriftTracker
from backend.api.factories import WiredApp, build_wired_app
from backend.api.logging import configure_logging
from backend.api.routes import router
from backend.api.settings import ApiSettings
from backend.api.telemetry import Telemetry


def create_app(*, wired: WiredApp | None = None) -> FastAPI:
    """
    Build the FastAPI app. Pass `wired` to inject a pre-built dependency set
    (tests do this with InMemoryRunStore + FakeLLM); leave None for prod.
    """

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        owns_wired = wired is None
        if owns_wired:
            settings = ApiSettings()
            configure_logging(level=settings.log_level)
            built = await build_wired_app(settings)
        else:
            assert wired is not None
            configure_logging(level=wired.settings.log_level)
            built = wired

        telemetry = Telemetry()
        drift = DriftTracker()

        app.state.wired = built
        app.state.run_store = built.run_store
        app.state.telemetry = telemetry
        app.state.drift = drift
        app.state.runner = AssessmentRunner(
            deps=built.deps,
            run_store=built.run_store,
            telemetry=telemetry,
            drift=drift,
        )
        try:
            yield
        finally:
            if owns_wired:
                await built.aclose()

    app = FastAPI(
        title="Boussole",
        version="0.7.0",
        description=(
            "Sovereign EU AI Act pre-assessment agent. Every legal claim is "
            "cited against Regulation (EU) 2024/1689; output is a technical "
            "pre-assessment that supports qualified legal review, not legal advice."
        ),
        lifespan=lifespan,
    )
    app.include_router(router)
    return app


app = create_app()
