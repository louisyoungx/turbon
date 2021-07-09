import os, json, urllib.parse
from Logger.logger import logger
from http.server import BaseHTTPRequestHandler
from Config.settings import config
from Message.message import sendFriendMessage

# Document https://docs.python.org/3.9/library/http.server.html

class RequestHandler(BaseHTTPRequestHandler):
    '''处理请求并返回页面'''

    # 处理一个GET请求
    def do_GET(self):
        self.rootPath = config.path() + "/Static"
        url = self.requestline[4:-9]
        request_data = {} # 存放GET请求数据
        try:
            if url.find('?') != -1:
                req = url.split('?', 1)[1]
                url = url.split('?', 1)[0]
                parameters = req.split('&')
                for i in parameters:
                    key, val = i.split('=', 1)
                    request_data[key] = val
        except:
            logger.error("URL Format Error")
        if (url == "/"):
            self.home()
        elif ("/api" in url):
            self.api(url[4:], request_data)
        else:
            self.file(url)

    def log_message(self, format, *args):
        SERVER_LOGGER = eval(config.settings("Logger", "SERVER_LOGGER"))
        if SERVER_LOGGER:
            logger.info(format % args)
        else:
            pass

    def home(self):

        file_path = self.rootPath + "/index.html"
        home_page_file = open(file_path, 'r')
        content = str(home_page_file.read())

        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content.encode())

    def file(self, url):
        file_name = url.split("/")[-1]
        file_sys_path = self.rootPath + url[:-len(file_name)]
        file_path = ""
        for root, dirs, files in os.walk(file_sys_path):
            for file in files:
                if file == file_name:
                    file_path = os.path.join(root, file)
                else:
                    continue
        if file_path != "":
            self.send_response(200)
        if file_path == "":
            # file_path = self.rootPath + "/404.html" # Hard Code
            self.noFound()
        elif file_name[-5:] == ".html":
            self.send_header("Content-Type", "text/html")
        elif file_name[-4:] == ".css":
            self.send_header("Content-Type", "text/css")
        elif file_name[-3:] == ".js":
            self.send_header("Content-Type", "application/javascript")
        elif file_name[-4:] == ".png":  # 二进制文件
            self.send_header("Content-Type", "img/png")
            file_page_file = open(file_path, 'rb')
            self.end_headers()
            self.wfile.write(file_page_file.read())
            return
        elif file_name[-4:] == ".jpg":  # 二进制文件
            self.send_header("Content-Type", "img/jpg")
            file_page_file = open(file_path, 'rb')
            self.end_headers()
            self.wfile.write(file_page_file.read())
            return
        elif file_name[-4:] == ".ico":  # 二进制文件
            self.send_header("Content-Type", "img/ico")
            file_page_file = open(file_path, 'rb')
            self.end_headers()
            self.wfile.write(file_page_file.read())
            return

        file_page_file = open(file_path, 'r')
        content = str(file_page_file.read())
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content.encode())

    def api(self, url, request_data):
        # ----------------------------------------------------------------
        # 此处写API
        if (url == "/log"):
            content = logger_records()
        elif (url[:11] == "/changeInfo"):
            changeInfo(request_data)
            content = "200"
        else:
            content = "No Response"

        # ----------------------------------------------------------------
        jsondict = {}
        jsondict["data"] = content
        res = json.dumps(jsondict)
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.send_header("Content-Length", str(len(res)))
        self.end_headers()
        self.wfile.write(res.encode())

    def noFound(self):
        self.file("/404.html")


def changeInfo(request_data):
    message = request_data["message"]
    message = urllib.parse.unquote(message)
    sendFriendMessage(message, 1462648167)

def logger_records():
    file_path = config.path() + config.settings("Logger", "FILE_PATH") + config.settings("Logger", "FILE_NAME")
    file_page_file = open(file_path, 'r')
    return str(file_page_file.read())


# 返回码
class ErrorCode(object):
    OK = "HTTP/1.1 200 OK"
    NOT_FOUND = "HTTP/1.1 404.html Not Found"

# Content类型
class ContentType(object):
    HTML = 'text/html'
    CSS = "text/css"
    JavaScript = "application/javascript"
    PNG = 'img/png'
