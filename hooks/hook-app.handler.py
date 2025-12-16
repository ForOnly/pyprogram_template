# @description: 
# @author: licanglong
# @date: 2025/6/25 9:04
# hook-task_executor.task.py
from PyInstaller.utils.hooks import collect_submodules

# 把 handlers 及其所有子包全部打进 hiddenimports
hiddenimports = collect_submodules('app.handler')
