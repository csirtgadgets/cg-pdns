import logging
import time
from models import Log


class SQLiteHandler(logging.Handler):
    """
    Logging handler with database target.

    Based on Vinay Sajip's DBHandler class (http://www.red-dove.com/python_logging.html)  # noqa
    """

    def __init__(self, session=None):
        logging.Handler.__init__(self)
        self.session = session

    def formatDBTime(self, record):
        record.dbtime = time.strftime("%Y-%m-%d %H:%M:%S",
                                      time.localtime(record.created))

    def emit(self, record):
        # Use default formatting:
        self.format(record)
        # Set the database time up:
        # self.formatDBTime(record)
        if record.exc_info:
            record.exc_text = logging._defaultFormatter.formatException(record.exc_info)  # noqa
        else:
            record.exc_text = ""
        # Insert log record:
        lr = Log(threadName=record.threadName,
                 name=record.name,
                 process=record.process,
                 processName=record.processName,
                 module=record.module,
                 levelno=record.levelno,
                 exception=record.exc_text,
                 lineno=record.lineno,
                 message=record.message,
                 funcName=record.funcName,
                 levelname=record.levelname
                 )
        self.session.add(lr)
