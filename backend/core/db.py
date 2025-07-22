# core/db.py
import json
import os

from sqlalchemy.pool import SingletonThreadPool, QueuePool
from sqlmodel import SQLModel, Session, create_engine
from contextlib import contextmanager
 
from core.settings import settings

# export environment variables
USER_FILE = settings.USER_FILE
DATABASE_URL = settings.DATABASE_URL

# === File-based user store (temporary IdP layer) ===
def load_users():
    if not os.path.exists(USER_FILE):
        return {"users": []}
    with open(USER_FILE, "r") as f:
        return json.load(f)

def save_users(users):
    with open(USER_FILE, "w") as f:
        json.dump(users, f, indent=2)

# === Business SQLModel DB ===
# SQLite-specific config (used for SQLite):
engine = create_engine(
    DATABASE_URL,
    echo=True
)

# MySQL-compatible config (used for MySQL):
# engine = create_engine(
#     DATABASE_URL,
#     echo=True,
#     poolclass=QueuePool  # use a pool suited for MySQL connections
# )

def init_db():
    SQLModel.metadata.create_all(engine)

def get_session():
    session = Session(engine)
    try:
        yield session
    finally:
        session.close()

# @contextmanager
# def session_scope():
#     with Session(engine) as session:
#         yield session