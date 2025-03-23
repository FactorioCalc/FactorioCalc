from .core import *

def toPythonName(name):
    """Convert all ``-`` to ``_``"""
    return name.replace('-','_')

def toClassName(name):
    """Convert `name` to title case."""
    return name.title().replace('-','')

def asItem(item):
    if item is None:
        return item
    if isinstance(item, str):
        item = itmByName[item]
    if not isinstance(item, Ingredient):
        raise TypeError(f'invalid type for item: {type(item)}')
    return item
