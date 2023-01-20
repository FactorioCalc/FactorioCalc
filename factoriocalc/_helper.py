from .core import *

def toPythonName(name):
    return name.replace('-','_')

def asItem(item):
    if item is None:
        return item
    if isinstance(item, str):
        item = itm.byName[item]
    if not isinstance(item, Ingredient):
        raise TypeError(f'invalid type for item: {type(item)}')
    return item
