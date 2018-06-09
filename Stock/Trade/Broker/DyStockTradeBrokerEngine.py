from EventEngine.DyEvent import *
from ..DyStockTradeCommon import *
from .YhNew.YhTrader import YhTrader
from .Simu.SimuTrader import *


class DyStockTradeBrokerEngine(object):
    """ 券商交易接口引擎 """

    traderMap = {
                 'yh': YhTrader,

                 'simu1': SimuTrader1,
                 'simu2': SimuTrader2,
                 'simu3': SimuTrader3,
                 'simu4': SimuTrader4,
                 'simu5': SimuTrader5,
                 'simu6': SimuTrader6,
                 'simu7': SimuTrader7,
                 'simu8': SimuTrader8,
                 'simu9': SimuTrader9,
                 }

    def __init__(self, eventEngine, info):
        self._eventEngine = eventEngine
        self._info = info

        self._traders = {}

        self._registerEvent()

    def _registerEvent(self):
        self._eventEngine.register(DyEventType.stockLogin, self._stockLoginHandler, DyStockTradeEventHandType.brokerEngine)
        self._eventEngine.register(DyEventType.stockLogout, self._stockLogoutHandler, DyStockTradeEventHandType.brokerEngine)

    def _stockLoginHandler(self, event):
        broker = event.data['broker']

        # create trader instance
        trader = self.traderMap[broker](self._eventEngine, self._info)

        # login
        trader.login()

        # sync pos
        trader.syncPos()

        # update account
        trader.updateAccount()

        self._traders[broker] = trader

    def _stockLogoutHandler(self, event):
        broker = event.data['broker']
        oneKeyHangUp = True if event.data.get('oneKeyHangUp') else False # 是否是一键挂机导致的交易接口退出

        trader = self._traders[broker]

        trader.logout(oneKeyHangUp)

        del self._traders[broker]