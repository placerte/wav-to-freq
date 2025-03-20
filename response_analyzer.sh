#!/bin/bash

#Activate the virtual environment if it exists

if [[ -d ".venv" ]]; then
	source .venv/bin/activate 2>/dev/null || source .venv/Scripts/activate
fi

# Run the python script
python main.py
