from sqlalchemy import Column, ForeignKey, Integer, String, \
                       Index, Table, DateTime
from sqlalchemy import create_engine
from sqlalchemy_utils.models import Timestamp
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker, backref
import sqlalchemy.exc

Base = declarative_base()


class queries(Base, Timestamp):
    __tablename__ = 'queries'
    __table_args__ = {'sqlite_autoincrement': True}
    id = Column(Integer, autoincrement=True, primary_key=True)
    collector = Column(String(64), nullable=False)
    tz = Column(String(3), nullable=False)
    qname = Column(String(256), nullable=False, index=True)
    qtype = Column(String(16), nullable=False)
    answers = relationship("answers",
                           cascade="all, delete-orphan")


class answers(Base, Timestamp):
    __tablename__ = 'answers'
    __table_args__ = {'sqlite_autoincrement': True}
    id = Column(Integer, autoincrement=True, primary_key=True)
    query_id = Column(Integer, ForeignKey('queries.id'), nullable=False)
    query = relationship(queries, backref=backref("queries",
                         cascade="all, delete-orphan"))
    atype = Column(String(16), nullable=False)
    answer = Column(String(256), nullable=False)
    ttl = Column(Integer, nullable=False)


class Log(Base, Timestamp):
    __tablename__ = 'log'
    __table_args__ = {'sqlite_autoincrement': True}
    id = Column(Integer, autoincrement=True, primary_key=True)
    name = Column(String(128))
    levelno = Column(Integer, index=True)
    levelname = Column(String(32), index=True)
    message = Column(String(256))
    args = Column(String(128))
    module = Column(String(32))
    funcName = Column(String(32))
    lineno = Column(Integer)
    exception = Column(String(256))
    process = Column(Integer)
    processName = Column(String(32))
    thread = Column(String(256))
    threadName = Column(String(256))


def attach(dbstr):
    try:
        engine = create_engine(dbstr, echo=False)
        # engine = create_engine('mysql+pymysql://root@localhost/pdns', echo=False)  # noqa
        DBSession = sessionmaker(bind=engine)
        conn = DBSession()
        Base.metadata.create_all(engine)
        conn.commit()
        return conn

    except sqlalchemy.exc.OperationalError as e:
        print "Failed to connect to {0} :: {1}".format(dbstr, e)
        return None
