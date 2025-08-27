#!/usr/bin/env bash
set -e
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements-dev.txt
echo "Now: copy .env.example to .env, fill it, then run 'make run-ftg'."
