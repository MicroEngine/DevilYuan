from ..DyStockCtaTemplate import *


class DyST_BankIntraDaySpread(DyStockCtaTemplate):

    name = 'DyST_BankIntraDaySpread'
    chName = '银行日内价差'

    backTestingMode = 'bar1m'

    broker = 'yh'

    # 策略实盘参数
    codes = ['601988.SH', '601288.SH', '601398.SH', '601939.SH']
    spread = 0.5


    def __init__(self, ctaEngine, info, state, strategyParam=None):
        super().__init__(ctaEngine, info, state, strategyParam)

        self._curInit()

    def _onOpenConfig(self):
        self._monitoredStocks.extend(self.codes)

    def _curInit(self, date=None):
        pass

    @DyStockCtaTemplate.onOpenWrapper
    def onOpen(self, date, codes=None):
        # 当日初始化
        self._curInit(date)

        self._onOpenConfig()

        return True

    def onTicks(self, ticks):
        """
            收到行情TICKs推送
            @ticks: {code: DyStockCtaTickData}
        """
        
        if self._curPos:
            code = list(self._curPos)[0]
            tick = ticks.get(code)
            if tick is None:
                return

            increase = (tick.price - tick.preClose)/tick.preClose*100

            spreads = {}
            for code_ in self.codes:
                if code == code_:
                    continue
                
                tick_ = ticks.get(code_)
                if tick_ is None:
                    continue

                spread = increase - (tick_.price - tick_.preClose)/tick_.preClose*100
                if spread >= self.spread:
                    spreads[code_] = spread

            codes = sorted(spreads, key=lambda k: spreads[k], reverse=True)
            if codes:
                self.closePos(ticks.get(code))

                self.buyByRatio(ticks.get(codes[0]), 50, self.cAccountLeftCashRatio)
                    
        else:
            increases = {}
            for code in self.codes:
                tick = ticks.get(code)
                if tick is None:
                    continue

                increases[code] = (tick.price - tick.preClose)/tick.preClose*100

            codes = sorted(increases, key=lambda k: increases[k])
            if codes:
                self.buyByRatio(ticks.get(codes[0]), 50, self.cAccountLeftCashRatio)
            
    def onBars(self, bars):
        self.onTicks(bars)
