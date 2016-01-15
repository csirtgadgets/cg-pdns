#!/usr/bin/env python

import lzma
import sqlite3
import logging
import argparse
import tornado.web
import tornado.escape
from tornado.ioloop import IOLoop
from tornado.httpserver import HTTPServer

import __builtin__

from sqlalchemy import create_engine
LOG_FORMAT = '%(asctime)s - %(levelname)s - %(name)s[%(lineno)s] - %(message)s'
__builtin__.logging.basicConfig(level=logging.DEBUG, format=LOG_FORMAT)
__builtin__.conn = None

parser = argparse.ArgumentParser(
    description='passive dns collector')

parser.add_argument('--verbose', '-v', action='count')
parser.add_argument('--port', '-p', type=int,
                    help='listen on this port')
parser.add_argument('--apikey', '-a', type=str,
                    help='magic key needed to talk to us')
                          
class BaseHandler(tornado.web.RequestHandler):
    def add_headers(self, mimetype="text/json", status=200):
        self.set_header("Content-Type", mimetype)
        self.set_header("Access-Control-Allow-Origin", "''")
        self.set_status(status)
    
    def nok(self, msg=''):
        return { '_status': 'NOK', '_message': msg }
    
    def ok(self, msg=''):
        return { '_status': 'OK', '_message': msg }
        
class VersionHandler(BaseHandler):
    def get(self):
        response = self.ok()
        response.update( { 'version': '1.0.0' } )
        self.add_headers()
        self.write(response)

class Incoming(BaseHandler):
	def get(self):
		self.add_headers(status=404)
		self.write(self.nok("go away"))

	def post(self):
		response = self.ok()
		data = self.request.body
		try:
			lz = lzma.LZMADecompressor()
			jd = lz.decompress(data)
			j = json.loads(jd)
			print j
		
def make_app():
	settings = {}
	application = tornado.web.Application([
        (r"/pdns/version", VersionHandler),
        (r"/pdns/post", Incoming),
        ], **settings)
    return application

def main():
    app = make_app()
    http_server = tornado.httpserver.HTTPServer(app,
    #    ssl_options={
    #        "certfile": os.path.join(data_dir, "server.crt"),
    #        "keyfile": os.path.join(data_dir, "server.key"),
    #    }
    )
    logger.info("Connect to DB")

    #loghandler = Util.sqlite_loghandler.SQLiteHandler(session)
    #logger.addHandler(loghandler)

    __builtin__.conn = sqlite3.connect('example.db')
    
    logger.info("Starting on 8888...")
    http_server.listen(8888)

    logger.info("Started. Entering ioloop...")
    tornado.ioloop.IOLoop.instance().start()

if __name__ == "__main__":
    main()


