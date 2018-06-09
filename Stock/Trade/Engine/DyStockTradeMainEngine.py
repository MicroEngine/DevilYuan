from DyCommon.DyCommon import *

from EventEngine.DyEventEngine import *

from ..DyStockTradeCommon import *

from ..Market.DyStockMarketEngine import *
from ..Strategy.DyStockCtaEngine import *
from ..Broker.DyStockTradeBrokerEngine import *
from ...Data.Engine.DyStockDataEngine import *
#from ..QQ.DyStockTradeQQMsgEngine import *
from ..WeChat.DyStockTradeWxEngine import *
#from ..Rpc.DyStockTradeRpcEngine import DyStockTradeRpcEngine


class DyStockTradeMainEngine(object):
    def __init__(self):
        self._eventEngine = DyEventEngine(DyStockTradeEventHandType.nbr)
        self._info = DyInfo(self._eventEngine)

        self._dataEngine = DyStockDataEngine(self._eventEngine, self._info, False)

        # 实时行情监控
        self._stockMarketEngine = DyStockMarketEngine(self._eventEngine, self._info)

        # 交易接口
        self._stockBrokerEngine = DyStockTradeBrokerEngine(self._eventEngine, self._info)

        # 策略CTA引擎
        self._stockCtaEngine = DyStockCtaEngine(self._dataEngine, self._eventEngine, self._info)

        # QQ消息
        #self._QQMsgEngine = DyStockTradeQQMsgEngine(self._eventEngine, self._info)

        # 微信
        self._wxEngine = DyStockTradeWxEngine(self._eventEngine, self._info)

        # RPC
        #self._rpcEngine = DyStockTradeRpcEngine(self._eventEngine, self._info)

        self._eventEngine.start()

    @property
    def eventEngine(self):
        return self._eventEngine

    @property
    def info(self):
        return self._info

    def exit(self):
        """退出程序前调用，保证正常退出"""        
        # 停止事件引擎
        self._eventEngine.stop()
    
    


