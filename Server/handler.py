"""HTTP Server Handler
This module builds on BaseHTTPServer by implementing the standard GET
and HEAD requests in a fairly straightforward manner.

Document https://docs.python.org/3.9/library/http.server.html
"""
import json
import os
import time
import sys
import argparse
import posixpath
import shutil
import mimetypes
import re
import signal
from io import StringIO, BytesIO
from urllib.parse import quote
from urllib.parse import unquote
from http.server import HTTPServer
from http.server import BaseHTTPRequestHandler
try:
    from html import escape
except ImportError:
    from cgi import escape

from Config import config
from Logger import logger
from Server.router import router


static_path = config.path + config.Server.static_path

class RequestHandler(BaseHTTPRequestHandler):
    """
    HTTP request handler with GET/HEAD/POST commands.
    """
    server_version = "simple_http_server/" + config.Server.version

    def do_GET(self):
        """Serve a GET request."""
        fd = self.send_head()
        if fd:
            shutil.copyfileobj(fd, self.wfile)
            fd.close()

    def do_HEAD(self):
        """Serve a HEAD request."""
        fd = self.send_head()
        if fd:
            fd.close()

    def do_POST(self):
        """Serve a POST request."""
        r, info = self.deal_post_data()
        print(r, info, "by: ", self.client_address)
        f = BytesIO()
        f.write(b'<!DOCTYPE html PUBLIC "-//W3C//DTD HTML 3.2 Final//EN">')
        f.write(b"<html>\n<title>Upload Result Page</title>\n")
        f.write(b"<body>\n<h2>Upload Result Page</h2>\n")
        f.write(b"<hr>\n")
        if r:
            f.write(b"<strong>Success:</strong>")
        else:
            f.write(b"<strong>Failed:</strong>")
        f.write(info.encode('utf-8'))
        f.write(b"<br><a href=\"%s\">back</a>" % self.headers['referer'].encode('utf-8'))
        f.write(b"<hr><small>Powered By: freelamb, check new version at ")
        f.write(b"<a href=\"https://github.com/freelamb/simple_http_server\">")
        f.write(b"here</a>.</small></body>\n</html>\n")
        length = f.tell()
        f.seek(0)
        self.send_response(200)
        self.send_header("Content-type", "text/html;charset=utf-8")
        self.send_header("Content-Length", str(length))
        self.end_headers()
        if f:
            shutil.copyfileobj(f, self.wfile)
            f.close()

    def log_message(self, format, *args):
        server_logger = config.Logger.server_logger
        if server_logger:
            logger.info(format % args)
        else:
            pass

    def deal_post_data(self):
        boundary = self.headers["Content-Type"].split("=")[1].encode('utf-8')
        remain_bytes = int(self.headers['content-length'])
        line = self.rfile.readline()
        remain_bytes -= len(line)
        if boundary not in line:
            return False, "Content NOT begin with boundary"
        line = self.rfile.readline()
        remain_bytes -= len(line)
        fn = re.findall(r'Content-Disposition.*name="file"; filename="(.*)"', line.decode('utf-8'))
        if not fn:
            return False, "Can't find out file name..."
        path = translate_path(self.path)
        fn = os.path.join(path, fn[0])
        while os.path.exists(fn):
            fn += "_"
        line = self.rfile.readline()
        remain_bytes -= len(line)
        line = self.rfile.readline()
        remain_bytes -= len(line)
        try:
            out = open(fn, 'wb')
        except IOError:
            return False, "Can't create file to write, do you have permission to write?"

        pre_line = self.rfile.readline()
        remain_bytes -= len(pre_line)
        while remain_bytes > 0:
            line = self.rfile.readline()
            remain_bytes -= len(line)
            if boundary in line:
                pre_line = pre_line[0:-1]
                if pre_line.endswith(b'\r'):
                    pre_line = pre_line[0:-1]
                out.write(pre_line)
                out.close()
                return True, "File '%s' upload success!" % fn
            else:
                out.write(pre_line)
                pre_line = line
        return False, "Unexpect Ends of data."

    def send_head(self):
        """Handle with URL"""
        if self.is_api():
            return self.api()
        else:
            return self.static()

    def is_api(self):
        """Check if the request is a api request"""
        if self.path.startswith('/api'):
            return True
        else:
            return False

    def api(self):
        """Common api for Get and POST"""
        url = self.requestline[4:-9]
        request_data = {}  # 存放GET请求数据
        try:
            if url.find('?') != -1:
                req = url.split('?', 1)[1]
                url = url.split('?', 1)[0]
                parameters = req.split('&')
                for i in parameters:
                    key, val = i.split('=', 1)
                    request_data[key] = val
        except Exception as e:
            logger.error("URL Format Error")
        url = url[4:]
        content = router(url, request_data)  # 此处进入路由
        localtime = time.localtime(time.time())
        date = \
            localtime.tm_year.__str__() + '-' + \
            localtime.tm_mon.__str__() + '-' + \
            localtime.tm_mday.__str__() + ' ' + \
            localtime.tm_hour.__str__() + ':' + \
            localtime.tm_min.__str__() + ':' + \
            localtime.tm_sec.__str__()
        jsonDict = {"data": content, "time": date}
        res = json.dumps(jsonDict)
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.send_header("Content-Length", str(len(res)))
        self.end_headers()
        self.wfile.write(res.encode())
        return None

    def static(self):
        """Common code for GET and HEAD commands.
        This sends the response code and MIME headers.
        Return value is either a file object (which has to be copied
        to the output file by the caller unless the command was HEAD,
        and must be closed by the caller under all circumstances), or
        None, in which case the caller has nothing further to do.
        """
        path = translate_path(self.path)
        if os.path.isdir(path):
            if not self.path.endswith('/'):
                # redirect browser - doing basically what apache does
                self.send_response(301)
                self.send_header("Location", self.path + "/")
                self.end_headers()
                return None
            for index in "index.html", "index.htm":
                index = os.path.join(path, index)
                if os.path.exists(index):
                    path = index
                    break
            else:
                return self.list_directory(path)
        content_type = self.guess_type(path)
        try:
            # Always read in binary mode. Opening files in text mode may cause
            # newline translations, making the actual size of the content
            # transmitted *less* than the content-length!
            f = open(path, 'rb')
        except IOError:
            self.send_error(404, "File not found")
            return None
        self.send_response(200)
        self.send_header("Content-type", content_type)
        fs = os.fstat(f.fileno())
        self.send_header("Content-Length", str(fs[6]))
        self.send_header("Last-Modified", self.date_time_string(fs.st_mtime))
        self.end_headers()
        return f

    def list_directory(self, path):
        """Helper to produce a directory listing (absent index.html).
        Return value is either a file object, or None (indicating an
        error).  In either case, the headers are sent, making the
        interface the same as for send_head().
        """
        try:
            list_dir = os.listdir(path)
        except os.error:
            self.send_error(404, "No permission to list directory")
            return None
        list_dir.sort(key=lambda a: a.lower())
        f = BytesIO()
        display_path = escape(unquote(self.path))
        f.write(b'<!DOCTYPE html PUBLIC "-//W3C//DTD HTML 3.2 Final//EN">')
        f.write(b"<html>\n<title>Directory listing for %s</title>\n" % display_path.encode('utf-8'))
        f.write(b"<body>\n<h2>Directory listing for %s</h2>\n" % display_path.encode('utf-8'))
        f.write(b"<hr>\n")
        f.write(b"<form ENCTYPE=\"multipart/form-data\" method=\"post\">")
        f.write(b"<input name=\"file\" type=\"file\"/>")
        f.write(b"<input type=\"submit\" value=\"upload\"/></form>\n")
        f.write(b"<hr>\n<ul>\n")
        for name in list_dir:
            fullname = os.path.join(path, name)
            display_name = linkname = name
            # Append / for directories or @ for symbolic links
            if os.path.isdir(fullname):
                display_name = name + "/"
                linkname = name + "/"
            if os.path.islink(fullname):
                display_name = name + "@"
                # Note: a link to a directory displays with @ and links with /
            f.write(b'<li><a href="%s">%s</a>\n' % (quote(linkname).encode('utf-8'), escape(display_name).encode('utf-8')))
        f.write(b"</ul>\n<hr>\n</body>\n</html>\n")
        length = f.tell()
        f.seek(0)
        self.send_response(200)
        self.send_header("Content-type", "text/html;charset=utf-8")
        self.send_header("Content-Length", str(length))
        self.end_headers()
        return f

    def guess_type(self, path):
        """Guess the type of a file.
        Argument is a PATH (a filename).
        Return value is a string of the form type/subtype,
        usable for a MIME Content-type header.
        The default implementation looks the file's extension
        up in the table self.extensions_map, using application/octet-stream
        as a default; however it would be permissible (if
        slow) to look inside the data to make a better guess.
        """

        base, ext = posixpath.splitext(path)
        if ext in self.extensions_map:
            return self.extensions_map[ext]
        ext = ext.lower()
        if ext in self.extensions_map:
            return self.extensions_map[ext]
        else:
            return self.extensions_map['']

    if not mimetypes.inited:
        mimetypes.init()  # try to read system mime.types
    extensions_map = mimetypes.types_map.copy()
    extensions_map.update({
        '': 'application/octet-stream',  # Default
        '.py': 'text/plain',
        '.c': 'text/plain',
        '.h': 'text/plain',
    })


def translate_path(path):
    """Translate a /-separated PATH to the local filename syntax.
    Components that mean special things to the local file system
    (e.g. drive or directory names) are ignored.  (XXX They should
    probably be diagnosed.)
    """
    # abandon query parameters
    path = path.split('?', 1)[0]
    path = path.split('#', 1)[0]
    path = posixpath.normpath(unquote(path))
    words = path.split('/')
    words = filter(None, words)
    path = static_path
    for word in words:
        drive, word = os.path.splitdrive(word)
        head, word = os.path.split(word)
        if word in (os.curdir, os.pardir):
            continue
        path = os.path.join(path, word)
    return path


def signal_handler(signal, frame):
    print("You choose to stop me.")
    exit()