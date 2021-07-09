import json
from http.server import HTTPServer
from Logger.logger import logger
from Server.handler import RequestHandler
from Config.settings import config

def server():
    DEBUG = eval(config.settings("Debug", "DEBUG"))
    LOCAL_HOST = config.settings("Server", "LOCAL_HOST")
    SERVER_HOST = config.settings("Server", "SERVER_HOST")
    PORT = eval(config.settings("Server", "PORT"))
    if DEBUG == True:
        name = LOCAL_HOST
    else:
        name = SERVER_HOST
    port = PORT
    host = LOCAL_HOST
    serverAddress = (host, port)
    logger.info("http://{}:{}/".format(name, port))
    server = HTTPServer(serverAddress, RequestHandler)
    server.serve_forever()
