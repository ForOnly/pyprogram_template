# @description: 
# @author: licanglong
# @date: 2025/9/24 14:03
import logging
import os

# 设置环境变量
os.environ["APP_PATH"] = os.getenv('APP_PATH') or os.path.abspath(os.path.dirname(__file__))  # noqa

from app.App import App

App.DEFAULT_LOG_FILE = "logs/app.log"


class AppImpl(App):
    def run(self):
        # start work
        logging.info("application startup")


if __name__ == '__main__':
    AppImpl().start()
