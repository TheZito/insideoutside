from pathlib import Path

from alembic import command
from alembic.config import Config

_MIGRATIONS_DIR = Path(__file__).parent


def _alembic_config(db_path: str) -> Config:
    cfg = Config()
    cfg.set_main_option("script_location", str(_MIGRATIONS_DIR))
    cfg.set_main_option("sqlalchemy.url", f"sqlite:///{db_path}")
    return cfg


def apply_migrations(db_path: str) -> None:
    """Apply any pending Alembic migrations to the SQLite database at db_path.

    Idempotent: safe to call when the database is already at head.
    """
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    cfg = _alembic_config(db_path)
    command.upgrade(cfg, "head")
