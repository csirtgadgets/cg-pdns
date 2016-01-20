#!/usr/bin/env python

__version__ = "1.0.0"

import backports.lzma as lzma
import json
import time
import logging
import argparse
import datetime
import traceback
import tornado.web
import tornado.escape
import tornado.httpserver

from models.models import Query, Answer, attach
import models.sqlite_loghandler
from sqlalchemy.sql import text

LOG_FORMAT = '%(asctime)s - %(levelname)s - %(name)s[%(lineno)s] - %(message)s'
logging.basicConfig(level=logging.DEBUG, format=LOG_FORMAT)
logger = logging.getLogger(__name__)

import __builtin__
__builtin__.conn = None
__builtin__.engine = None

parser = argparse.ArgumentParser(
    description='passive dns collector')

parser.add_argument('--verbose', '-v', action='count')
parser.add_argument('--port', '-p', type=int, default=8888,
                    help='listen on this port')
parser.add_argument('--apikey', '-a', type=str, required=True,
                    help='magic key needed to talk to us')
parser.add_argument('--db', '-d', type=str,
                    default="sqlite:////data/pdns.db",
                    help='db connect string, default sqlite:////data/pdns.db')
                    # mysql+pymysql://root@localhost/pdns
args = parser.parse_args()


class BaseHandler(tornado.web.RequestHandler):
    def add_headers(self, mimetype="text/json", status=200):
        self.set_header("Content-Type", mimetype)
        self.set_header("Access-Control-Allow-Origin", "''")
        self.set_status(status)

    def nok(self, msg=''):
        return {'_status': 'NOK', '_message': msg}

    def ok(self, msg=''):
        return {'_status': 'OK', '_message': msg}


class VersionHandler(BaseHandler):
    def get(self):
        response = self.ok()
        response.update({'version': __version__})
        self.add_headers()
        self.write(response)


class Incoming_ORM(BaseHandler):
    def get(self):
        self.add_headers(status=404)
        self.write(self.nok("go away"))

    def post(self):
        def ts2dt(ts):
            return datetime.datetime.fromtimestamp(ts)

        response = self.ok()
        data = self.request.body
        conn.begin()
        try:
            lz = lzma.LZMADecompressor()
            jd = lz.decompress(data)
            j = json.loads(jd)
            logger.info("Got post with len {0} uncompressed {1}".format(len(data), len(jd)))
            assert 'apikey' in j and j['apikey'] == args.apikey, "not authorized"

            txt = time.time()
            txc = 0

            for query in j['dns']:
                Q = Query(collector = j['identity'],
                          tz = query['tz'],
                          insertedat = ts2dt(query['ts']),
                          qname = query['query'],
                          qtype = query['qtype'])
                conn.add(Q)
                conn.flush()
                conn.refresh(Q)
                txc += 1
            
                for ans_type, ans_ttl, ans_str in query['answers']:
                    A = Answer(atype = ans_type,
                               ttl = ans_ttl,
                               answer = ans_str,
                               query = Q)
                    conn.add(A)
                    txc += 1

            conn.commit()
            txdur = time.time() - txt
            logger.info("Wrote {0} records in {1}s .. {2} rec/sec".format(txc, txdur, txc/txdur))
             
        except AssertionError as e:
            logger.error("invalid (or no) apikey")
            response = self.nok("{0}".format(e))
            conn.rollback()

        except Exception as e:
            logger.error("hmm {0}".format(e))
            print e
            traceback.print_exc()
            conn.rollback()
            response = self.nok("post failed")

        self.add_headers()
        self.write(response)


class Incoming_Core(BaseHandler):
    def get(self):
        self.add_headers(status=404)
        self.write(self.nok("go away"))

    def post(self):
        def ts2dt(ts):
            return datetime.datetime.fromtimestamp(ts)

        response = self.ok()
        data = self.request.body
        with engine.begin() as con:
            try:

                t0 = time.time()
                lz = lzma.LZMADecompressor()
                jd = lz.decompress(data)
                j = json.loads(jd)
                assert 'apikey' in j and j['apikey'] == args.apikey, "not authorized"
                logger.info("Got post from {3} with len {0} (uncompressed {1}) in {2}s".format(j['identity'], len(data), len(jd), time.time()-t0))  # noqa

                txt = time.time()
                txc = 0

                for query in j['dns']:
                    ts_str = ts2dt(query['ts'])
                    res = con.execute(Query.__table__.insert(),
                             {"collector": j['identity'],
                             "tz": query['tz'],
                             "insertedat": ts_str,
                             "qname": query['query'],
                             "qtype": query['qtype']})

                    qid = res.inserted_primary_key[0]
                    txc += 1

                    ans_list = []

                    for ans_type, ans_ttl, ans_str in query['answers']:
                        ans_list.append({"atype": ans_type,
                                         "ttl": ans_ttl,
                                         "answer": ans_str,
                                         "query_id": qid})
                    if len(ans_list) > 0:
                        con.execute(Answer.__table__.insert(), ans_list)
                        txc += len(ans_list)

                txdur = time.time() - txt
                logger.info("Wrote {0} records in {1}s .. {2} rec/sec".format(txc, txdur, txc/txdur))
             
            except AssertionError as e:
                logger.error("invalid (or no) apikey")
                response = self.nok("{0}".format(e))

            except Exception as e:
                logger.error("hmm {0}".format(e))
                traceback.print_exc()
                response = self.nok("post failed")

        self.add_headers()
        self.write(response)


class StatsHandler(BaseHandler):
    def get(self, apikey):
        def do_select(_s):
            with engine.connect() as conn:
                try:
                    s = text(_s)
                    r = conn.execute(s).fetchone()
                    return r[0]
                except:
                    return 0

        response = self.nok("not authorized")

        if apikey is not None and apikey == args.apikey:
            response = self.ok()
            q_last_hour = do_select("select count(*) from queries where insertedat >= datetime('now', '-1 hour');")
            col_last_hour = do_select("select count(distinct(collector)) from queries where insertedat >= datetime('now', '-1 hour');")
            response.update({'qrec_last_hour': q_last_hour,
                             'collectors_reporting_last_hour': col_last_hour})

        self.add_headers()
        self.write(response)

def make_app():
    settings = {}
    application = tornado.web.Application([
        (r"/pdns/version", VersionHandler),
        (r"/pdns/stats/(\S+)", StatsHandler),
        (r"/pdns/post", Incoming_Core),
        ], **settings)
    return application


def main():
    app = make_app()
    logger.info("Connect to DB")
    __builtin__.conn, __builtin__.engine = attach(args.db)
    if conn is not None:
        loghandler = models.sqlite_loghandler.SQLiteHandler(conn)
        logger.addHandler(loghandler)

        http_server = tornado.httpserver.HTTPServer(app)

        logger.info("Starting on {0}...".format(args.port))
        http_server.listen(args.port)

        logger.info("Started. Entering ioloop...")
        tornado.ioloop.IOLoop.instance().start()
    else:
        print "Failed to connect to db: ", args.db

if __name__ == "__main__":
    main()
