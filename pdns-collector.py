#!/usr/bin/env python
"""Extract from a pcap file of all dns queries:
time, query, answer, type, ttl

somewhat poached from justin.. 
"""
import sys
import gzip
import time
import json
import lzma
import pcapy
import urllib2
import logging
import datetime
import argparse
import dns.message
import dns.rdatatype
import backports.lzma as xz
from pytz import reference

# records in this dict will totes be collected

TYPES = {
    dns.rdatatype.A: 'A',
    dns.rdatatype.AAAA: 'AAAA',
    dns.rdatatype.CNAME: 'CNAME',
    dns.rdatatype.TXT: 'TXT',
    dns.rdatatype.NS: 'NS'
}

parser = argparse.ArgumentParser(
    description='passive dns collector')

parser.add_argument('--verbose', '-v', action='count')
parser.add_argument('--write', '-w', type=str,
                    help='write results as json to a file')

pgroup_ex = parser.add_mutually_exclusive_group()
pgroup_ex.add_argument('--file', '-f', type=str,
                    help='pcap file to process')
pgroup_ex.add_argument('--post', '-p', type=str,
                    help='post json results to a url, requires -a')

parser.add_argument('--identity', '-I', type=str,
                    required=True,
                    help='a string to uniquely identify us')
parser.add_argument('--apikey', '-a', type=str,
                    help='apikey to use when posting json results to a url')
parser.add_argument('--iface', '-i', type=str,
                    help='network iface to snoop (use sudo)')
parser.add_argument('--count', '-c', type=int, default=100,
                    help='numbe of packets to collect before performing a --post (default 100)')
args = parser.parse_args()

LOG_FORMAT = '%(asctime)s - %(levelname)s - %(name)s[%(lineno)s] - %(message)s'
logging.basicConfig(level=logging.DEBUG, format=LOG_FORMAT)
logging.getLogger("scapy.runtime").setLevel(logging.ERROR)
logger = logging.getLogger(__name__)

from scapy.all import *

def date(d):
    return datetime.datetime.fromtimestamp(d).strftime("%Y-%m-%dT%H:%M:%S")

class fileProcessor:
    """
    To be replaced with scapy...
    """
    def __init__(self):
        self.data = []
        self.localtz = reference.LocalTimezone()

    def __call__(self, header, data):

        ts, _ =  header.getts()
        try:
            m = dns.message.from_wire(data[42:])
        except:
            return
        query = self.get_query(m)
        if not query:
            return

        ans_set = set()
        for answer, type, ttl in self.get_answers(m):
            ans_set.add((answer, type))

        self.data.append({
                'ts': ts, 
                'tz': self.localtz.tzname(datetime.datetime.fromtimestamp(ts)),
                'query': query, 
                'answer': list(ans_set)})
                
    def get_answers(self, m):
        for a in m.answer:
            if a.rdtype not in TYPES: continue
            for i in a:
                yield i.to_text().lower(), TYPES[a.rdtype], a.ttl

    def get_query(self, m):
        try :
            query = m.question[0].to_text().split()[0]
        except IndexError:
            return None
        if query.endswith("."):
            query = query[:-1]
        return query.lower()

class networkProcessor:
    def __init__(self, identity, apikey, url, count):
        self.data = []
        self.localtz = reference.LocalTimezone()
        self.apikey = apikey
        self.url = url
        self.count = count
        self.ccount = 0
        self.last_emit = time.time()
        self.identity = identity

    def __call__(self, p):
        ts = time.time()

        rr_set = set()

        if p.haslayer(DNS):

            qtype = None
            if p.qdcount > 0 and isinstance(p.qd, scapy.layers.dns.DNSQR):
                query = p.qd.qname
                qtype = p.qd.qtype

            if qtype is None or qtype not in TYPES:
                return

            if p.ancount > 0 and isinstance(p.an, scapy.layers.dns.DNSRR):
                for i in range(p.ancount):
                    an = p.an[i]
                    if an.type in TYPES:
                        rr_set.add((TYPES[an.type], an.ttl, an.rdata))
            
            if p.nscount > 0 and isinstance(p.ns, scapy.layers.dns.DNSRR):
                for i in range(p.nscount):
                    ns = p.ns[i]
                    if ns.type in TYPES:
                        rr_set.add((TYPES[ns.type], ns.ttl, ns.rdata))

            ts = time.time()
            self.data.append({
            		'ts': ts, 
                    'tz': self.localtz.tzname(datetime.datetime.fromtimestamp(ts)),
                    'query': query, 
                    'qtype': TYPES[qtype],
                    'answers': list(rr_set)})

            self.ccount += 1
            if self.ccount > self.count:
                self.ccount = 0
                try:
                    t0 = time.time()
                    j = json.dumps({'apikey': self.apikey, 'dns': self.data, 'identity': self.identity})
                    lz = lzma.LZMACompressor()
                    jc = lz.compress(j)
                    jc += lz.flush()
                    logger.info("compression took {0}s".format(time.time()-t0))

                    logger.info("emit {1}b ({2}b) after {3}s {0}/s".format(self.count/(time.time()-self.last_emit), len(jc), len(j), time.time()-self.last_emit))  # noqa
                    self.last_emit = time.time()
                    self.data = []
                    self.do_post(jc)
                except Exception as e:
                    logger.error("Something bad happened for this batch {0}".format(e))
                    self.data = []
                    self.last_emit = time.time()

    def do_post(self, _data):
    	"""
    	TODO: thread so this doesn't stall the collector
    	"""
        headers = {'Content-Type': 'application/json'}

        try:
            t0 = time.time()
            req = urllib2.Request(self.url, data=_data, headers=headers)
    	    _rsp = urllib2.urlopen(req, timeout=15)
            body = _rsp.read()
            rsp = json.loads(body)
            t1 = time.time() - t0
            logger.info("Records posted in {0}s".format(t1))
            assert rsp['_status'] == 'OK', "{0} failed: {1}".format(base, rsp['_message'])

        except urllib2.URLError as e:
            logger.error("Server is down: {0}".format(e))

        except urllib2.HTTPError as e:
            logger.error("Server said {0}. Discarding this batch of records.".format(e))

        except ValueError:
            logger.error("Server returned something other than JSON, maybe nothing at all.")

        except AssertionError:
            logger.error("Server denied us.")


def main():
    if args.file is not None:
        s = fileProcessor()
        pcap = pcapy.open_offline(args.file)
        pcap.loop(0, s)
        f = open(args.file, "w")
        f.write(json.dumps(s.data))
        f.close()
    elif args.post:
        if args.apikey:
            s = networkProcessor(args.identity, args.apikey, args.post, args.count or 100)
            sniff(iface=args.iface, store=0, filter="udp port 53 and ( udp[10] & 0x04 != 0 )", prn=s)
        else:
            print "--apikey required with --post"

if __name__ == "__main__":
    main()