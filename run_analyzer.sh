#!/usr/bin/env bash
# ==============================================================================
# SAP BO & Tomcat Log Analyzer - Entry Script
# ==============================================================================
# This script ensures dependencies are met, sets up a virtual environment,
# and runs the log analyzer tool.
#
# Usage: ./run_analyzer.sh [arguments...]
# Example: ./run_analyzer.sh --no-ai --max-errors 50
# ==============================================================================

# Exit immediately if a command exits with a non-zero status
set -e

# Configuration
VENV_DIR="venv"
REQUIREMENTS_FILE="requirements.txt"
MAIN_SCRIPT="main.py"

echo "========================================================"
echo "    SAP BO & Tomcat Log Analyzer Setup & Runner"
echo "========================================================"

# 1. Check for Python 3
if ! command -v python3 &> /dev/null; then
    echo "[ERROR] Python 3 could not be found."
    echo "This tool requires Python 3.7 or higher."
    echo "Please install Python 3 and try again."
    exit 1
fi

PYTHON_BIN="python3"

# 2. Check for pip
if ! command -v pip3 &> /dev/null; then
    echo "[WARNING] pip3 could not be found. Trying python3 -m pip..."
    if ! "$PYTHON_BIN" -m pip --version &> /dev/null; then
        echo "[ERROR] pip could not be found."
        echo "Please install python3-pip and try again."
        exit 1
    fi
fi

# 3. Setup Virtual Environment
if [ ! -d "$VENV_DIR" ]; then
    echo "[INFO] Virtual environment not found. Creating one in '$VENV_DIR'..."
    "$PYTHON_BIN" -m venv "$VENV_DIR"
    echo "[INFO] Virtual environment created successfully."
else
    echo "[INFO] Using existing virtual environment in '$VENV_DIR'."
fi

# 4. Activate Virtual Environment
echo "[INFO] Activating virtual environment..."
source "$VENV_DIR/bin/activate"

# 5. Check and Install Dependencies
if [ -f "$REQUIREMENTS_FILE" ]; then
    echo "[INFO] Checking and installing dependencies from '$REQUIREMENTS_FILE'..."
    # Always ensure we have the latest pip
    pip install --upgrade pip --quiet
    
    # Install requirements
    pip install -r "$REQUIREMENTS_FILE" --quiet
    echo "[INFO] Dependencies are satisfied."
else
    echo "[WARNING] '$REQUIREMENTS_FILE' not found. Skipping dependency installation."
fi

# 6. Ensure .env file exists (copy template if needed)
if [ ! -f ".env" ] && [ -f ".env.example" ]; then
    echo "[INFO] .env file not found. Copying .env.example to .env..."
    cp .env.example .env
    echo "[WARNING] Please review the newly created .env file and update API keys/paths if using AI."
fi

# 7. Run the Analyzer
echo "========================================================"
echo "    Running Analyzer..."
echo "========================================================"

# Pass all incoming arguments to the python script
python "$MAIN_SCRIPT" "$@"

# Store the exit code of the python script
EXIT_CODE=$?

# 8. Deactivate Virtual Environment
deactivate

echo "========================================================"
if [ $EXIT_CODE -eq 0 ]; then
    echo "[SUCCESS] Analysis completed successfully."
else
    echo "[ERROR] Analyzer exited with code $EXIT_CODE."
fi

exit $EXIT_CODE
