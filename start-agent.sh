#!/bin/bash
# Script to easily set up the coding agent environment

# This script no longer sets the GEMINI_API_KEY directly.
# It will guide the user to set it up via a .env file.

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo "Virtual environment not found. Creating one with Python 3.12..."
    uv venv --python=3.12

    if [ $? -ne 0 ]; then
        echo "Failed to create virtual environment. Make sure uv is installed."
        exit 1
    fi

    echo "Installing dependencies..."
    source .venv/bin/activate
    # Ensure all dependencies from pyproject.toml are installed, including langchain_google_genai if it's still needed
    # and any other direct dependencies of the project.
    # The `-e .` command should handle installing the project and its defined dependencies.
    uv pip install -e .

    # Install the IPython kernel (optional, for Jupyter notebooks)
    # Consider making this truly optional or removing if not core to the agent's function.
    python -m ipykernel install --user --name=miga --display-name "Migration Agent"

    echo "Initial setup complete!"
else
    echo "Using existing virtual environment."
fi

# Activate the virtual environment
source .venv/bin/activate

# Check for .env file and guide user if not present or API key is placeholder
if [ ! -f ".env" ] || grep -q "YOUR_GEMINI_API_KEY_HERE" ".env"; then
    echo ""
    echo "--------------------------------------------------------------------------"
    echo "IMPORTANT: API Key Setup Needed"
    echo "--------------------------------------------------------------------------"
    if [ ! -f ".env" ]; then
        echo "The .env file is missing."
        echo "Please copy .env.template to .env: "
        echo "  cp .env.template .env"
        echo "Then, edit the .env file and replace 'YOUR_GEMINI_API_KEY_HERE' with your actual Gemini API key."
    elif grep -q "YOUR_GEMINI_API_KEY_HERE" ".env"; then
        echo "The .env file exists, but it seems you haven't replaced the placeholder API key."
        echo "Please edit .env and replace 'YOUR_GEMINI_API_KEY_HERE' with your actual Gemini API key."
    fi
    echo "The agent needs this key to function, especially for 'migration-agent exec'."
    echo "--------------------------------------------------------------------------"
    echo ""
fi


echo "Migration Agent environment ready."
echo "You can now use 'migration-agent plan' or 'migration-agent exec'."
echo "Example:"
echo "  migration-agent plan"
echo "  migration-agent exec"
echo ""
echo "To run the legacy interactive agent (if needed):"
echo "  python src/main.py"
echo ""
echo "The application will attempt to load the GEMINI_API_KEY from the .env file."
# The script will no longer automatically start an agent.
# It will set up the environment, and the user can then run the desired command.
