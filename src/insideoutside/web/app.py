from fastapi import FastAPI
from sqlalchemy import text

from insideoutside.storage.db import Database


def create_app(db: Database) -> FastAPI:
    app = FastAPI(title="insideoutside")
    app.state.db = db

    @app.get("/healthz")
    def healthz() -> dict:
        with db.session() as session:
            session.execute(text("SELECT 1"))
        return {"status": "ok"}

    from insideoutside.web.routes.dashboard import router as dashboard_router
    from insideoutside.web.routes.signals import router as signals_router
    from insideoutside.web.routes.thresholds import router as thresholds_router

    app.include_router(signals_router)
    app.include_router(thresholds_router)
    app.include_router(dashboard_router)

    return app
