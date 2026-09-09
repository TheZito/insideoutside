from fastapi import FastAPI
from sqlalchemy import text

from openinsider_tracker.storage.db import Database


def create_app(db: Database) -> FastAPI:
    app = FastAPI(title="OpenInsider Tracker")
    app.state.db = db

    @app.get("/healthz")
    def healthz() -> dict:
        with db.session() as session:
            session.execute(text("SELECT 1"))
        return {"status": "ok"}

    from openinsider_tracker.web.routes.dashboard import router as dashboard_router
    from openinsider_tracker.web.routes.signals import router as signals_router
    from openinsider_tracker.web.routes.thresholds import router as thresholds_router

    app.include_router(signals_router)
    app.include_router(thresholds_router)
    app.include_router(dashboard_router)

    return app
