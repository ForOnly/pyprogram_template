# @description: 
# @author: licanglong
# @date: 2025/9/24 14:04
import importlib
import pkgutil

from app import handler

for finder, name, ispkg in pkgutil.iter_modules(handler.__path__, handler.__name__ + "."):
    importlib.import_module(name)
