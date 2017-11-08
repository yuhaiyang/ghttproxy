import logging
import urllib.parse
import time
import re
from http.client import HTTPConnection
import sys
import random
import json

import gevent
from gevent import socket
from gevent.pywsgi import WSGIHandler, WSGIServer
from gevent.pool import Pool
from gevent.event import Event

log = logging.getLogger(__name__)

CHUNKSIZE = 65536


def pipe_socket(client, remote):
    def copy(a, b, finish):
        while not finish.is_set():
            try:
                data = a.recv(CHUNKSIZE)
                if not data:
                    break
                b.sendall(data)
            except:
                break
        finish.set()

    finish = Event()
    finish.clear()
    threads = [
        gevent.spawn(copy, client, remote, finish),
        gevent.spawn(copy, remote, client, finish),
    ]
    [t.join() for t in threads]
    client.close()
    remote.close()


class ProxyHandler(WSGIHandler):
    """ override WSGIHandler.handle() to process https proxy
    """

    def handle(self):
        try:
            while self.socket is not None:
                self.time_start = time.time()
                self.time_finish = 0
                result = self.handle_one_request()
                if result is None:
                    break
                if result is True:
                    if self.command == "CONNECT":
                        break
                    else:
                        continue
                self.status, response_body = result
                self.socket.sendall(response_body)
                if self.time_finish == 0:
                    self.time_finish = time.time()
                self.log_request()
                break

            if self.socket and hasattr(self, 'command') and \
                        self.command == "CONNECT" and self.environ.get('__ghttproxy.tunnelconn', None):
                pipe_socket(self.socket,
                            self.environ.get('__ghttproxy.tunnelconn'))
        finally:
            if self.socket is not None:
                try:
                    try:
                        self.socket._sock.recv(16384)
                    finally:
                        self.socket._sock.close()
                        self.socket.close()
                except socket.error:  # @UndefinedVariable
                    pass
            self.__dict__.pop('socket', None)
            self.__dict__.pop('rfile', None)

    """ override WSGIHandler.get_environ() to pass raw headers and raw path to environ
    """

    def get_environ(self):
        env = super(ProxyHandler, self).get_environ()
        env['__ghttproxy.rawheaders'] = self.headers.headers
        env['PATH_INFO'] = self.path.split('?', 1)[0]
        return env


# some of below code are copied and modifed from "meek/wsgi/reflect.py"
# at https://git.torproject.org/pluggable-transports/meek.git


# Limits a file-like object to reading only n bytes. Used to keep limit
# wsgi.input to the Content-Length, otherwise it blocks.
class LimitedReader(object):
    def __init__(self, f, n):
        self.f = f
        self.n = n

    def __getattr__(self, name):
        return getattr(self.f, name)

    def read(self, size=None):
        if self.n <= 0:
            return ""
        if size is not None and size > self.n:
            size = self.n
        data = self.f.read(size)
        self.n -= len(data)
        return data


def set_forwarded_for(environ, headers):
    if environ['REMOTE_ADDR'] in ('127.0.0.1', '::1') and \
            'X-Forwarded-For' not in headers:
        # don't add header if we are forwarding localhost,
        return

    s = headers.get('X-Forwarded-For', '')
    if s:
        forwarders = s.split(", ")
    else:
        forwarders = []
    addr = environ['REMOTE_ADDR']
    if addr:
        forwarders.append(addr)
    if forwarders:
        headers['X-Forwarded-For'] = ", ".join(forwarders)


def reconstruct_url(environ):
    path = environ.get('PATH_INFO')
    if path.startswith("http://"):
        url = path
    else:
        host = environ.get('HTTP_HOST')
        url = 'http://' + host + path

    query = environ.get('QUERY_STRING', '')
    if query:
        url += '?' + query
    return url


def get_destination(environ):
    if environ["REQUEST_METHOD"] == "CONNECT":
        port = 443
    else:
        port = 80

    host = environ.get('HTTP_HOST', '').lower().split(":")
    path = environ.get('PATH_INFO', '').lower()
    req = urllib.parse.urlparse(path)
    # first process requeset line
    if req.scheme:
        if req.scheme != "http":
            raise Exception('invalid scheme in request line')
        netloc = req.netloc.split(":")
        if len(netloc) == 2:
            return netloc[0], int(netloc[1])
        else:
            return req.netloc, port
    elif req.netloc:
        raise Exception('invalid scheme in request line')

    # then process host
    if len(host) == 2:
        return host[0], int(host[1])
    else:
        return host[0], port


NON_FORWARD_HEADERS = (
    'proxy-connection',
    'host', )


def copy_request(environ):
    method = environ["REQUEST_METHOD"]
    url = reconstruct_url(environ)

    headers = []
    content_length = environ.get("CONTENT_LENGTH")
    if content_length:
        body = LimitedReader(environ["wsgi.input"], int(content_length))
    else:
        body = ""

    raw = environ['__ghttproxy.rawheaders']
    for header in raw:
        key, value = header.split(':', 1)
        if not key:
            continue
        if key.strip().lower() in NON_FORWARD_HEADERS:
            continue
        headers.append((key.strip(), value.strip()))
    headers.append(("Connection", "Keep-Alive"))
    headers = dict(headers)
    #if url == 'http://oa.hillstonenet.com:8088/wxclient/app/attendance/addForEc':
    #    if method == 'POST':
    #        request_body = bytes.decode(environ["wsgi.input"].read(int(content_length)))
    #        log.info(request_body)
    #        request_body=re.sub(r'sign\.lng=\d+\.+\d+&','sign.lng=120.434617&',request_body)
    #        request_body=re.sub(r'sign\.lat=\d+\.+\d+&','sign.lat=31.323565&',request_body)
    #        request_body=re.sub(r'sign\.address=[^&]+&','sign.address==%E6%B1%9F%E8%8B%8F%E7%9C%81%E8%8B%8F%E5%B7%9E%E5%B8%82%E8%99%8E%E4%B8%98%E5%8C%BA%E8%8B%8F%E5%B7%9E%E7%A7%91%E6%8A%80%E5%9F%8E%E5%B1%B1%E7%9F%B3%E7%BD%91%E7%A7%91%E5%A4%A7%E5%8E%A6&',request_body)
    #        log.info(request_body)
    #        body = request_body
    #        if 'Content-Length' in headers:
    #            del headers['Content-Length']
    return method, url, body, headers


class ProxyApplication(object):
    def __init__(self, timeout=60):
        self.timeout = timeout

    def http(self, environ, start_response):
        try:
            host, port = get_destination(environ)
            log.info("HTTP request to (%s:%d)" % (host, port))
            if host == '127.0.0.1':
                status = '200 OK'
                response_headers = [('Content-Type', 'text/plain')]
                start_response(status, response_headers)
                yield b'It\'s Work!'
                return
            method, url, body, headers = copy_request(environ)
            if 'wxclient/app/attendance/addForEc' in url:
                if method == 'POST':
                    body = u'{"signTime":"2017-11-08 14:15:28","success":false,"msg":"温馨提示:请先断开代理服务器","btnType":"2"}'
                    status = '200 OK'
                    response_headers = [('Content-Type', 'application/json;charset=UTF-8'), ('Content-Length', str(len(str.encode(body))))]
                    start_response(status, response_headers)
                    yield str.encode(body)
                    return
        except Exception as e:
            log.error("[Exception][http 400]: %s" % str(e))
            start_response("400 Bad Request", [("Content-Type",
                                                "text/plain; charset=utf-8")])
            yield "Bad Request"
            return

        try:
            # dismiss x-forwarders
            # set_forwarded_for(environ, headers)
            http_conn = socket.create_connection(
                (host, port), timeout=self.timeout)
            conn = HTTPConnection(host, port=port)
            conn.sock = http_conn
            if '/app/attendance/js/sign_ec.js' in url:
                # url = '/app/attendance/js/sign_ec.js?'+str(random.randint(0, 9999))
                #headers['If-None-Match'] = 'W/"10040-1502791023965"'
                print(url)

            u = urllib.parse.urlsplit(url)
            path = urllib.parse.urlunsplit(("", "", u.path, u.query, ""))
            # Host header put by conn.request
            conn.request(method, path, body, headers)
            resp = conn.getresponse()

            # start_response("%d %s" % (resp.status, resp.reason), resp.getheaders())
            # while True:
            #     data = resp.read(CHUNKSIZE)
            #     if not data:
            #         break
            #     yield data

            headers = resp.getheaders()
            for header in headers:
                if 'Content-Length' in header:
                    headers.remove(header)

            # lenths = len(data)
            # conten_lenth = ('Content-Length', str(lenths))
            # headers.append(conten_lenth)

            chunked_encoding = ('Transfer-Encoding', 'chunked')
            headers.append(chunked_encoding)
            if '/app/attendance/js/sign_ec.js' in url:
                # url = '/app/attendance/js/sign_ec.js?'+str(random.randint(0, 9999))
                # headers['If-None-Match'] = 'W/"10040-1502791023965"'
                log.info('Respone for %s' % url)
                for header in headers:
                    if 'Cache-Control' in header:
                        headers.remove(header)

                CacheControl = ('Cache-Control', 'public,max-age=31536000')
                headers.append(CacheControl)
                print(url)
            start_response("%d %s" % (resp.status, resp.reason), headers)
            while True:
                data = resp.read(CHUNKSIZE)
                if not data:
                    break
                if '/app/attendance/js/sign_ec.js' in url:
                    data = bytes.decode(data)
                    with open(sys.path[0]+"/config.json", 'r') as load_f:
                        load_dict = json.load(load_f)
                    # lng = float('%s%d' % (load_dict['lng'], random.randint(0, 999)))
                    # lat = float('%s%d' % (load_dict['lat'], random.randint(0, 999)))
                    # print(lng, ',', lat)
                    data = re.sub(
                        r'setLngLat\(lng, lat\) {',
                        'setLngLat(lng, lat) {\n\tlng=%s+Math.random()*1000/1000000;\n\tlat=%s+Math.random()*1000/1000000;\n' % (load_dict['lng'], load_dict['lat']),
                        data)
                    data = re.sub(r'定位点', '牛X的定位点', data)
                    ''' data = re.sub(r'longitude = position.coords.longitude;',
                                  'longitude = 116.404731;', data)
                    data = re.sub(r'latitude = position.coords.latitude;',
                                  'latitude = 39.905679";', data) '''
                    log.info(url + 'REPLACE++++++++++')
                    data = str.encode(data)
                if 'wxclient/app/attendance/addForEc' in url:
                    if method == 'POST':
                        data = bytes.decode(data)
                        log.info(data)
                        data = str.encode(data)
                yield data

            conn.close()
        except Exception as e:
            log.error("[Exception][http 500]: %s" % str(e))
            start_response("500 Internal Server Error",
                           [("Content-Type", "text/plain; charset=utf-8")])
            yield "Internal Server Error"
            return

    def tunnel(self, environ, start_response):
        try:
            host, port = get_destination(environ)
            log.info("CONNECT request to (%s:%d)" % (host, port))
        except Exception as e:
            log.error("[Exception][tunnel]: %s" % str(e))
            start_response("400 Bad Request", [("Content-Type",
                                                "text/plain; charset=utf-8")])
            return ["Bad Request"]

        try:
            tunnel_conn = socket.create_connection(
                (host, port), timeout=self.timeout)
            environ['__ghttproxy.tunnelconn'] = tunnel_conn
            start_response("200 Connection established", [])
            return []
        except socket.timeout:  # @UndefinedVariable
            log.error("Connection Timeout")
            start_response("504 Gateway Timeout",
                           [("Content-Type", "text/plain; charset=utf-8")])
            return ["Gateway Timeout"]
        except Exception as e:
            log.error("[Exception][https]: %s" % str(e))
            start_response("500 Internal Server Error",
                           [("Content-Type", "text/plain; charset=utf-8")])
            return ["Internal Server Error"]

    def application(self, environ, start_response):
        if environ["REQUEST_METHOD"] == "CONNECT":
            return self.tunnel(environ, start_response)
        else:
            return self.http(environ, start_response)


class HTTPProxyServer(object):
    def __init__(self, ip, port, app, log='default'):
        self.ip = ip
        self.port = port
        self.app = app
        self.server = WSGIServer(
            (self.ip, self.port),
            log=log,
            application=self.app.application,
            spawn=Pool(500),
            handler_class=ProxyHandler)

    def start(self):
        self.server.start()

    def run(self):
        self.server.serve_forever()

    def stop(self):
        self.server.stop()

    @property
    def closed(self):
        return self.server.closed


if __name__ == '__main__':
    logging.basicConfig(
        format='[%(asctime)s][%(name)s][%(levelname)s] - %(message)s',
        datefmt='%Y-%d-%m %H:%M:%S',
        level=logging.DEBUG, )
    #print(os.getcwd())
    print("Listening 0.0.0.0:", 65535)
    HTTPProxyServer("0.0.0.0", 65535, ProxyApplication()).run()
