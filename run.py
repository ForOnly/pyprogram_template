# @description: 
# @author: licanglong
# @date: 2025/9/24 14:03

import os

# 设置环境变量
os.environ["APP_PATH"] = os.path.abspath(os.path.dirname(__file__))  # noqa

if __name__ == '__main__':
    import app  # noqa

    # run
