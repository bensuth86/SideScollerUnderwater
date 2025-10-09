# src/helpers/reflection.py
import importlib


def resolve_class(dotted_path):
    """
    Dynamically import and return a class from a dotted path string.

    Example: 'src.sprites.enemy.Enemy'
    """
    try:
        module_path, class_name = dotted_path.rsplit('.', 1)
        module = importlib.import_module(module_path)
        return getattr(module, class_name)
    except (ImportError, AttributeError) as e:
        raise ImportError(f"Cannot resolve class from '{dotted_path}': {e}") from e
