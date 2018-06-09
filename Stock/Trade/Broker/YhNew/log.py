from DyCommon.DyCommon import *


class log(object):
    """
        log adaptor for easytrader
    """

    dyInfo = None
    
    def info(text):
        log.dyInfo.print(text, DyLogData.info)

    def error(text):
        log.dyInfo.print(text, DyLogData.error)

    def warning(text):
        log.dyInfo.print(text, DyLogData.warning) 

