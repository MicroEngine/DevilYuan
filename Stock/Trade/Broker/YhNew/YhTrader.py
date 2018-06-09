import os

from ..UiTrader import UiTrader
from .YhUiTrader import YHClientTrader
from .log import log

from DyCommon.DyCommon import *
from ...DyStockTradeCommon import *


class YhTrader(UiTrader):
    """ 银河证券窗口交易类 """
    brokerName = '银河证券'
    broker = 'yh'

    # consts set by config menu
    exePath = None
    account = None
    password = None

    heartBeatTimer = 0 # no heart beat

    curEntrustHeaderNoIndex = 11
    curEntrustHeaderStateIndex = 4


    def __init__(self, eventEngine, info):
        super().__init__(eventEngine, info)

        log.dyInfo = info

        self._uiClient = YHClientTrader(DyCommon.createPath('Stock/Program/Temp'))

    def _login(self):
        user = self.account
        password = self.password
        exePath = self.exePath

        try:
            self._uiClient.login(user, password, exePath)
        except Exception as ex:
            self._info.print('登录[银河证券]异常:{}'.format(ex), DyLogData.error)
            return False

        return True

    @UiTrader.retryWrapper
    def _logout(self, oneKeyHangUp=False):
        return self._uiClient.exit()

    def getBalance(self, parse=True, fromBroker=True):
        """
            获取账户资金状况
            @return: header, [[item]]
        """
        if self._balanceHeader is not None and not fromBroker:
            return self._balanceHeader, self._balance

        df = self._uiClient.balance

        header, rows = list(df), df.values.tolist()

        self._balanceHeader = header
        self._balance = rows
        
        return header, rows

    def getPositions(self, fromBroker=True):
        """
            获取账户持仓
            @return: header, [[item]], autoForegroundColName
        """
        if self._positionHeader is not None and not fromBroker:
            return self._positionHeader, self._positions, '参考盈亏'

        df = self._uiClient.position

        header, rows = list(df), df.values.tolist()

        self._positionHeader = header
        self._positions = rows

        return header, rows, '参考盈亏'

    def getCurEntrusts(self):
        """
            获取当日委托
            @return: header, [[item]]
        """
        df = self._uiClient.today_entrusts

        return list(df), df.values.tolist()

    def getCurDeals(self):
        """
            获取当日成交
            @return: header, [[item]]
        """
        df = self._uiClient.today_trades

        return list(df), df.values.tolist()

    def onTicks(self, ticks):
        """
            For UI
            update stock price related data, e.g. stock market value, stock price, PnL
        """
        if self._balance is None or self._positions is None:
            return

        # positions
        marketValue = 0 # 账户市值
        for pos in self._positions:
            code = DyStockCommon.getDyStockCode(pos[0])
            tick = ticks.get(code)
            if tick is None:
                self._info.print('银河证券: 无法获取{0}({1})的Tick数据'.format(code, pos[1]), DyLogData.warning)
                marketValue += float(pos[9])
                continue

            pos[9] = tick.price*float(pos[2]) # 市值
            pos[11] = tick.price # 最新价格
            pos[7] = (tick.price - float(pos[-4]))*float(pos[2]) # 浮动盈亏

            marketValue += pos[9]

        # balance
        if self._positions:
            balance = self._balance[0]

            marketValueDelta = marketValue - float(balance[-2])
            balance[-2] = marketValue
            balance[-1] = float(balance[-1]) + marketValueDelta

    def refresh(self):
        self._uiClient.refresh()

    @UiTrader.retryWrapper
    def buy(self, code, name, price, volume):
        try:
            ret = self._uiClient.buy(code[:6], price, volume)
            if ret is None:
                return False
        except:
            return False

        return True

    @UiTrader.retryWrapper
    def sell(self, code, name, price, volume):
        try:
            ret = self._uiClient.sell(code[:6], price, volume)
            if ret is None:
                return False
        except:
            return False

        return True

    @UiTrader.retryWrapper
    def cancel(self, entrust):
        ret = self._uiClient.cancel_entrust(entrust.brokerEntrustId)

        message = ret['message']
        if  '错误' in message or 'unkown' in message:
            log.warning('银河证券客户端:撤单[{}({}), 委托号{}]错误:{}'.format(entrust.name, entrust.code, entrust.brokerEntrustId, message))
            return False

        return True