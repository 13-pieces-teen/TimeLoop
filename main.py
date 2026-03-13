"""TimeLoop: The Unspeakable Midnight -- Entry Point"""

import logging
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)

from src.ui.app import create_app

if __name__ == "__main__":
    app = create_app()
    port = int(os.environ.get("PORT", 7860))
    app.launch(
        share=False,
        server_name="0.0.0.0",
        server_port=port,
        allowed_paths=["data/images"],
    )
