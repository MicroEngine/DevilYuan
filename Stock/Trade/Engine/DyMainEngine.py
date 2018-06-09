
from .DyEventEngine import *

from ..Market.DyStockMarketEngine import *
from ..Cta.DyCtaStockEngine import *
from ..DyStockTradeLog import *

class DyMainEngine(object):
    def __init__(self):
        self._eventEngine = DyEventEngine()

        self._log = DyStockTradeLog(self._eventEngine)

        # 实时行情监控
        self._stockMarketEngine = DyStockMarketEngine(self._eventEngine, self._log)

        # 扩展模块
        self._ctaStockEngine = DyCtaStockEngine(self._eventEngine, self._log)

        self._eventEngine.start()

    @property
    def eventEngine(self):
        return self._eventEngine

    def exit(self):
        """退出程序前调用，保证正常退出"""        
        # 停止事件引擎
        self._eventEngine.stop()
    
    


