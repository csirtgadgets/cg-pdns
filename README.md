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

```
 sql> select * from queries q, answers a where q.id = a.query_id and q.id = 3;
 created|updated|id|collector|tz|qname|qtype|created|updated|id|query_id|atype|answer|ttl
 2016-01-16 04:59:12.785510|2016-01-16 04:59:12.788643|3|foobar|EST|sis001.sextop1.info.|A|2016-01-16 04:59:12.789315|2016-01-16 04:59:12.789321|2|3|CNAME|ns1.qqsexygirl.com.|600
 2016-01-16 04:59:12.785510|2016-01-16 04:59:12.788643|3|foobar|EST|sis001.sextop1.info.|A|2016-01-16 04:59:12.789476|2016-01-16 04:59:12.789482|3|3|NS|f1g1ns2.dnspod.net.|86400
 2016-01-16 04:59:12.785510|2016-01-16 04:59:12.788643|3|foobar|EST|sis001.sextop1.info.|A|2016-01-16 04:59:12.789610|2016-01-16 04:59:12.789614|4|3|NS|f1g1ns1.dnspod.net.|86400

 sql> select * from queries where qname like '%google.com.';
 [many matching queries]
```

### Tables

```
 queries:
        insertedat DATETIME NOT NULL, 
        id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT, 
        collector VARCHAR(64) NOT NULL, 
        tz VARCHAR(3) NOT NULL, 
        qname VARCHAR(256) NOT NULL, 
        qtype VARCHAR(16) NOT NULL

 answers: 
        id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT, 
        query_id INTEGER NOT NULL, 
        atype VARCHAR(16) NOT NULL, 
        answer VARCHAR(256) NOT NULL, 
        ttl INTEGER NOT NULL, 
        FOREIGN KEY(query_id) REFERENCES queries (id)
        
```

# SQLite Performance Refs

 http://docs.sqlalchemy.org/en/latest/faq/performance.html#i-m-inserting-400-000-rows-with-the-orm-and-it-s-really-slow

 http://stackoverflow.com/questions/15778716/sqlite-insert-speed-slows-as-number-of-records-increases-due-to-an-index

# Archiver Reference Numbers

25M row count is sum of the two tables.


instance    | new db   | 25M row db 
------------|----------|------------
t2.small    | 7.0k/sec | 2.5k/sec     
sqlite      |          |            
------------|----------|------------
m4.large    | 7.5k/sec |
sqlite      |          |
------------|----------|------------
t2.small    | 1.5k/sec | 
db.t2.small |          |
mysql/mag   |          |
------------|----------|------------
t2.small    |    k/sec | 
db.t2.small |          |
mysql/ssd   |          |
------------|----------|------------
t2.small    | 1.9k/sec | 
db.m4.large |          |
mysql/mag   |          |
------------|----------|------------
m4.large    | 1.8k/sec | 
db.m4.large |          |
mysql/mag   |          |

