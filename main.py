import logging

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.api import router as credit_router
from app.config import settings
from app.db import Base, engine
from app.seed_db import seed_database


def create_app() -> FastAPI:
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    )
    logger = logging.getLogger(__name__)

    app = FastAPI(
        title=settings.project_name,
        version="2.0.0",
    )

    app.mount("/static", StaticFiles(directory="app/static"), name="static")

    app.include_router(credit_router)

    @app.on_event("startup")
    async def startup_event():
        logger.info("🚀 Starting Silky Credit & Behaviour Engine (ChatGPT 5.1)...")
        logger.info("📦 Creating tables (if not exist)...")
        Base.metadata.create_all(bind=engine)
        logger.info("🌱 Seeding demo data (if DB empty)...")
        seed_database()
        logger.info("✅ Startup complete.")

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
