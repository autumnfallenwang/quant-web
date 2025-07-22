#!/bin/bash

# Ensure this file is executable:
# chmod +x start_uvicorn_debug.sh

LOG_FILE="uvicorn_crash.log"

# Run Uvicorn with Python's faulthandler enabled, and full debug logging
python -X faulthandler -m uvicorn main:app \
  --host 0.0.0.0 \
  --port 8000 \
  --log-level debug \
  --reload \
  &> "$LOG_FILE"