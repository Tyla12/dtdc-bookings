#!/bin/bash
set -e

echo "Installing system dependencies for psycopg2..."
sudo apt-get update
sudo apt-get install -y libpq-dev python3-dev build-essential

echo "Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

echo "Build complete!"
