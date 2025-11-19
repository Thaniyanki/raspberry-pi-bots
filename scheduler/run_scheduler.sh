#!/bin/bash

# Activate the virtual environment (works for any username)
source ~/bots/scheduler/venv/bin/activate

# Run the scheduler Python script directly from GitHub
curl -sL "https://raw.githubusercontent.com/Thaniyanki/raspberry-pi-bots/main/scheduler/scheduler.py" | python3
