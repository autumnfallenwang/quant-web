# tests/conftest.py
import sys
from pathlib import Path

# Resolve backend/ folder and add it to sys.path
BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))