import ssl
import random
import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.poolmanager import PoolManager

from .DyTrader import *


class Ssl3HttpAdapter(HTTPAdapter):
    def init_poolmanager(self, connections, maxsize, block=False):
        self.poolmanager = PoolManager(num_pools=connections,
                                       maxsize=maxsize,
                                       block=block,
                                       ssl_version=ssl.PROTOCOL_TLSv1)


class WebTrader(DyTrader):
    """
        券商Web交易接口基类
    """
    name = 'Web'

    heartBeatTimer = 60
    pollingCurEntrustTimer = 1
    maxRetryNbr = 3 # 最大重试次数


    def __init__(self, eventEngine, info, configFile=None, accountConfigFile=None):
        super().__init__(eventEngine, info, configFile, accountConfigFile)

        self._httpAdapter = None

    def _preLogin(self):
        # 开始一个会话
        self._session = requests.session()
        if self._httpAdapter is not None:
            self._session.mount('https://', self._httpAdapter())

        # session headers
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64; Trident/7.0; rv:11.0) like Gecko'
            }
        self._session.headers.update(headers)

    def _postLogout(self):
        self._session.close()
