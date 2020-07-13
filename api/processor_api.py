import time
from threading import Thread
from queue import Queue
from multiprocessing.managers import BaseManager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse
import uvicorn
import os

class QueueManager(BaseManager): pass

class ProcessorAPI:
    """
    The Webgui object implements a fastapi application and acts as an interface for users.
    Once it is created it will act as a central application for viewing outputs.

    :param config: Is a ConfigEngine instance which provides necessary parameters.
    :param engine_instance:  A ConfigEngine object which store all of the config parameters. Access to any parameter
        is possible by calling get_section_dict method.
    """

    def __init__(self, config):
        self.config = config
        self._setup_queues()
        self._host = self.config.get_section_dict("API")["Host"]
        self._port = int(self.config.get_section_dict("API")["Port"])
        self.app = self.create_fastapi_app()

    def _setup_queues(self):
        QueueManager.register('get_cmd_queue')
        QueueManager.register('get_result_queue')
        self._queue_host = self.config.get_section_dict("CORE")["Host"]
        self._queue_port = int(self.config.get_section_dict("CORE")["QueuePort"])
        auth_key = self.config.get_section_dict("CORE")["QueueAuthKey"]
        self._queue_manager = QueueManager(address=(self._host, self._queue_port), authkey=auth_key)
        self._queue_manager.connect()
        self._cmd_queue = self._queue_manager.get_cmd_queue()
        self._result_queue = self._queue_manager.get_result_queue()

    def create_fastapi_app(self):
        # Create and return a fastapi instance
        app = FastAPI()

        if os.environ.get('DEV_ALLOW_ALL_ORIGINS', False):
            # This option allows React development server (which is served on another port, like 3000) to proxy requests
            # to this server.
            # WARNING: read this before enabling it in your environment:
            # https://medium.com/@stestagg/stealing-secrets-from-developers-using-websockets-254f98d577a0
            from fastapi.middleware.cors import CORSMiddleware
            app.add_middleware(CORSMiddleware, allow_origins='*', allow_credentials=True, allow_methods=['*'],
                               allow_headers=['*'])
        app.mount("/static", StaticFiles(directory="/repo/data/web_gui/static"), name="static")

        return app

    def start(self):
        uvicorn.run(self.app, host=self._host, port=self._port, log_level='info', access_log=False)
