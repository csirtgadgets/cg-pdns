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

25M row count is sum of the two tables. the EC2 T2 instance had a full supply of credits, so it could
burst to the maximum allowed. inserts arrived in batches of around 14k (900 KB). archiver times how
long it takes to insert each batch and prints to output (also records to Log table). average results
shown below as inserts-per-second. in all cases, db is single instance not clustered.


instance                              | new db   | 25M row db 
--------------------------------------|----------|------------
t2.small <sup>1</sup>                 | 7.0k/sec | 4.5k/sec     
t2.small <sup>5</sup>                 | 3.1k/sec |     
m4.large <sup>1</sup>                 | 7.5k/sec | 3.0k/sec
t2.small / db.t2.small <sup>2</sup>   | 1.5k/sec | 
t2.small / db.t2.small <sup>3</sup>   | 1.0k/sec | 
t2.small / db.m4.large <sup>2</sup>   | 1.9k/sec | 
m4.large / db.m4.large <sup>2</sup>   | 1.8k/sec | 
t2.small / db.r3.large <sup>4</sup>   | 0.9/sec  | 

1. local sqlite
2. mysql/magnetic
3. mysql/ssd (gen)
4. aurora
5. local mysql

