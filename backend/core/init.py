# core/init.py
import json
import os

from core.db import init_db
from core.settings import settings

# export environment variables
DATABASE_FOLDER = settings.DATABASE_FOLDER
USER_FILE = settings.USER_FILE

def init_database_folder():
    if not os.path.exists(DATABASE_FOLDER):
        os.makedirs(DATABASE_FOLDER)

def init_user_file():
    if not os.path.exists(USER_FILE):
        with open(USER_FILE, "w") as f:
            json.dump({"users": []}, f)

def run_all():
    init_database_folder()
    init_db()
    init_user_file()