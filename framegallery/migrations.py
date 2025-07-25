"""Database migration utilities for automatic schema updates."""
import logging
from pathlib import Path

from sqlalchemy import create_engine, text

from alembic import command
from alembic.config import Config
from framegallery.config import settings

logger = logging.getLogger(__name__)


def get_alembic_config() -> Config:
    """Get Alembic configuration."""
    # Get the project root directory
    project_root = Path(__file__).parent.parent
    alembic_cfg_path = project_root / "alembic.ini"

    if not alembic_cfg_path.exists():
        msg = f"Alembic configuration file not found at {alembic_cfg_path}"
        raise FileNotFoundError(msg)

    alembic_cfg = Config(str(alembic_cfg_path))

    # Override the database URL with the current settings
    database_url = f"sqlite:///{settings.database_path}"
    alembic_cfg.set_main_option("sqlalchemy.url", database_url)

    return alembic_cfg


def check_database_exists() -> bool:
    """Check if the database file exists and is accessible."""
    try:
        database_path = Path(settings.database_path)
        if not database_path.exists():
            logger.info("Database file does not exist, will be created during migration")
            # Ensure the parent directory exists
            database_path.parent.mkdir(parents=True, exist_ok=True)
            return False

        # Try to connect to the database
        engine = create_engine(f"sqlite:///{settings.database_path}")
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        logger.warning("Database connection check failed: %s", e)
        return False


def run_migrations() -> bool:
    """
    Run database migrations to the latest version.

    Returns:
        bool: True if migrations were successful, False otherwise

    """
    try:
        logger.info("Starting database migration process")

        # Check if database exists
        db_exists = check_database_exists()
        if not db_exists:
            logger.info("Database will be created during migration")

        # Get Alembic configuration
        alembic_cfg = get_alembic_config()

        # Run migrations to the latest version
        logger.info("Running migrations to head...")
        command.upgrade(alembic_cfg, "head")

        logger.info("Database migrations completed successfully")
    except Exception:
        logger.exception("Database migration failed")
        return False
    else:
        return True


def get_current_migration_version() -> str | None:
    """
    Get the current migration version of the database.

    Returns:
        str | None: Current migration version or None if not versioned

    """
    try:
        from alembic.runtime.migration import MigrationContext

        engine = create_engine(f"sqlite:///{settings.database_path}")
        with engine.connect() as conn:
            context = MigrationContext.configure(conn)
            return context.get_current_revision()
    except Exception as e:
        logger.warning("Could not determine current migration version: %s", e)
        return None


def validate_migration_state() -> bool:
    """
    Validate that the database is in a consistent migration state.

    Returns:
        bool: True if migration state is valid, False otherwise

    """
    try:
        current_version = get_current_migration_version()
        if current_version is None:
            logger.warning("Database is not under version control")
            return False

        logger.info("Current database migration version: %s", current_version)
    except Exception:
        logger.exception("Migration state validation failed")
        return False
    else:
        return True
