#!/bin/bash
set -e  # Stop immediately if any command fails

echo "-------------------------------"
echo "Starting build on Render..."
echo "-------------------------------"

# Upgrade pip first
echo "Upgrading pip..."
pip install --upgrade pip

# Install all Python dependencies
echo "Installing Python dependencies from requirements.txt..."
pip install -r requirements.txt

echo "-------------------------------"
echo "Build completed successfully!"
echo "-------------------------------"
