"""
config.py
---------
Central configuration module.

Reads runtime settings from the ``.env`` file located in the project root
(via :mod:`python-dotenv`) and exposes them as module-level constants.

Constants
---------
BACKEND_URL : str
    Base URL for the backend REST API.
    Defaults to ``http://localhost:5117`` when the environment variable is
    not set.
"""

import os
from dotenv import load_dotenv

# Load environment variables from the .env file in the root directory
load_dotenv()

# Define configuration variables
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:5117")
