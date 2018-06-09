from .DyTrader import *


class UiTrader(DyTrader):
    """
        券商窗口交易接口基类
    """
    name = 'UI'

    heartBeatTimer = 60
    pollingCurEntrustTimer = 5
    maxRetryNbr = 3 # 最大重试次数


    def __init__(self, eventEngine, info, accountConfigFile=None):
        super().__init__(eventEngine, info, None, accountConfigFile)

        self._balanceHeader = None
        self._positionHeader = None

    def _sendHeartBeat(self, event):
        self.refresh()
