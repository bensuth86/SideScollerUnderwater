import json


def load_json(filepath, encoding='utf-8'):
    """Load and return JSON data to dictionary."""
    with open(filepath, 'r', encoding=encoding) as f:
        return json.load(f)


def save_json(filepath, data, encoding='utf-8', indent=4):
    """Save Python data to a JSON file."""
    with open(filepath, 'w', encoding=encoding) as f:
        json.dump(data, f, indent=indent)