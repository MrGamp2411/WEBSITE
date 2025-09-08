from logging.config import fileConfig
from pathlib import Path
import sys

from alembic import context

sys.path.append(str(Path(__file__).resolve().parents[1]))
from database import Base, engine
import models  # noqa: F401

config = context.config
fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_online() -> None:
    connectable = engine
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


def run_migrations_offline() -> None:
    url = str(engine.url)
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
