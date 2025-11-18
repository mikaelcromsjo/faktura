import json
from pathlib import Path
from zoneinfo import ZoneInfo  # Python 3.9+

DATA_DIR = Path("./data")

# put in admin #TODO
# 
DEFAULT_TZ = "Europe/Stockholm"
SHOW_PRODUCTS_X_DAYS = 5;

def load_json(filename):
    path = DATA_DIR / filename

    # If file does not exist → create it with empty JSON object
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump({}, f, indent=2)
        return {}

    # If the file exists → try loading it
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        # If corrupted or unreadable → reset it
        with open(path, "w", encoding="utf-8") as f:
            json.dump({}, f, indent=2)
        return {}


