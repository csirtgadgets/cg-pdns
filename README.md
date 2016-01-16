## CG Passive DNS 

Tool for distributed passive DNS collection

### Motivation

1. Single script
2. Minimal library reliance (for the collector)
3. Central reporting
4. Compression

### Usage

 archiver% python ./pdns-archiver.py -d sqlite:////tmp/pdns.db -a 12345
 
 collector% sudo python ./pdns-collector.py -i bond0 -a 12345 -c 1000 -p http://archiver:8888/pdns/post 

### Fiddling

 select * from queries q, answers a where q.id = a.query_id and q.id = 3;
