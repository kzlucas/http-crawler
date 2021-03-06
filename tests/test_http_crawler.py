import pytest

try:
    from http.server import SimpleHTTPRequestHandler, HTTPServer
except ImportError:  # Python 2
    from SimpleHTTPServer import SimpleHTTPRequestHandler
    from BaseHTTPServer import HTTPServer

import os
import ssl
from multiprocessing import Process

import urllib3
from requests.exceptions import SSLError

import http_crawler

serving = False

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def serve():
    global serving

    if serving:
        return

    serving = True

    def _serve(dir, port, bad_ssl_cert=False):
        base_dir = os.path.join('tests', dir)
        os.chdir(base_dir)
        server = HTTPServer(('', port), SimpleHTTPRequestHandler)
        if bad_ssl_cert:
            server.socket = ssl.wrap_socket(server.socket,
                                            server_side=True,
                                            certfile=os.path.join(
                                                '..', 'cert.pem')
                                            )
        server.serve_forever()

    proc_site = Process(target=_serve, args=('site', 8000))
    proc_site.daemon = True
    proc_site.start()

    proc_external_site = Process(target=_serve, args=('external-site', 8001))
    proc_external_site.daemon = True
    proc_external_site.start()

    proc_bad_ssl = Process(target=_serve, args=('one-page-site', 8002, True))
    proc_bad_ssl.daemon = True
    proc_bad_ssl.start()


def test_crawl():
    serve()

    rsps = list(http_crawler.crawl('http://localhost:8000/'))

    assert len(rsps) == 13

    urls = [rsp.url for rsp in rsps]

    assert len(urls) == len(set(urls))
    assert set(urls) == {
        'http://localhost:8000/',
        'http://localhost:8000/pages/page-1/',
        'http://localhost:8000/pages/page-2/',
        'http://localhost:8000/pages/page-3/',
        'http://localhost:8000/assets/styles.css',
        'http://localhost:8000/assets/styles-2.css',
        'http://localhost:8000/assets/image.jpg',
        'http://localhost:8000/assets/script.js',
        'http://localhost:8000/assets/tile-1.jpg',
        'http://localhost:8000/assets/tile-2.jpg',
        'http://localhost:8000/assets/somefont.eot',
        'http://localhost:8000/assets/somefont.ttf',
        'http://localhost:8001/pages/page-1/',
    }


def test_crawl_follow_external_links_false():
    serve()

    rsps = list(http_crawler.crawl('http://localhost:8000/',
                                   follow_external_links=False))

    assert len(rsps) == 12

    urls = [rsp.url for rsp in rsps]

    assert len(urls) == len(set(urls))
    assert set(urls) == {
        'http://localhost:8000/',
        'http://localhost:8000/pages/page-1/',
        'http://localhost:8000/pages/page-2/',
        'http://localhost:8000/pages/page-3/',
        'http://localhost:8000/assets/styles.css',
        'http://localhost:8000/assets/styles-2.css',
        'http://localhost:8000/assets/image.jpg',
        'http://localhost:8000/assets/script.js',
        'http://localhost:8000/assets/tile-1.jpg',
        'http://localhost:8000/assets/tile-2.jpg',
        'http://localhost:8000/assets/somefont.eot',
        'http://localhost:8000/assets/somefont.ttf',
    }


def test_crawl_ignore_fragments_false():
    serve()

    rsps = list(http_crawler.crawl('http://localhost:8000/',
                                   ignore_fragments=False))

    # assert len(rsps) == 14

    urls = [rsp.url for rsp in rsps]

    # assert len(urls) == len(set(urls))
    assert set(urls) == {
        'http://localhost:8000/',
        'http://localhost:8000/pages/page-1/',
        'http://localhost:8000/pages/page-1/#anchor',
        'http://localhost:8000/pages/page-2/',
        'http://localhost:8000/pages/page-2/#anchor',
        'http://localhost:8000/pages/page-3/',
        'http://localhost:8000/pages/page-3/#anchor',
        'http://localhost:8000/assets/styles.css',
        'http://localhost:8000/assets/styles-2.css',
        'http://localhost:8000/assets/image.jpg',
        'http://localhost:8000/assets/script.js',
        'http://localhost:8000/assets/tile-1.jpg',
        'http://localhost:8000/assets/tile-2.jpg',
        'http://localhost:8000/assets/somefont.eot',
        'http://localhost:8000/assets/somefont.ttf',
        'http://localhost:8001/pages/page-1/',
        'http://localhost:8001/pages/page-1/#anchor',
    }


def test_extract_urls_from_html():
    with open(os.path.join('tests', 'site', 'index.html')) as f:
        content = f.read()

    urls = http_crawler.extract_urls_from_html(content)

    assert len(urls) == 13
    assert set(urls) == {
        '/',
        'http://localhost:8000/pages/page-1/',
        'http://localhost:8000/pages/page-1/#anchor',
        'http://localhost:8001/pages/page-1/',
        'http://localhost:8001/pages/page-1/#anchor',
        '/pages/page-2/',
        '/pages/page-2/#anchor',
        'pages/page-3/',
        'pages/page-3/#anchor',
        '/assets/styles.css',
        '/assets/image.jpg',
        '/assets/script.js',
        'mailto:example@example.org',
    }


def test_extract_urls_from_css():
    with open(os.path.join('tests', 'site', 'assets', 'styles.css')) as f:
        content = f.read()

    urls = http_crawler.extract_urls_from_css(content)

    assert len(urls) == 5
    assert set(urls) == {
        '/assets/styles-2.css',
        '/assets/tile-1.jpg',
        '/assets/somefont.eot',
        '/assets/somefont.ttf',
    }


def test_ssl_verify_false():
    serve()

    rsps = list(http_crawler.crawl('https://localhost:8002', verify=False))

    assert len(rsps) == 1


def test_ssl_verify_true():
    serve()

    with pytest.raises(SSLError):
        list(http_crawler.crawl('https://localhost:8002', verify=True))
