from ..DyStockTradeCommon import *


class DyStockCtaEngineExtra(object):
    """
        股票CTA引擎的功能扩展类
        辅助类，跟CTA Engine class之间是dependancy关系
    """


    def _getCashByRatio(accountManager, strategyCls, ratio, ratioMode):
        """
            根据模式，获取总现金
        """
        if ratioMode == strategyCls.cAccountLeftCashRatio:
            cash = accountManager.curCash - accountManager.getCurCapital()*ratio/100
            cash = max(0, cash)
            return cash

        elif ratioMode == strategyCls.cFixedCash:
            return ratio

        if ratioMode == strategyCls.cCodePos:
            cash = accountManager.getCurCodePosMarketValue(code)

        elif ratioMode == strategyCls.cPos:
            cash = accountManager.getCurPosMarketValue()

        elif ratioMode == strategyCls.cAccountCapital:
            cash = accountManager.getCurCapital()

        elif ratioMode == strategyCls.cAccountCash:
            cash = accountManager.curCash

        # 计算比例资金
        cash *= ratio/100

        return cash

    def buyByRatio(ctaEngine, accountManager, strategyCls, tick, ratio, ratioMode, signalInfo=None):
        code = tick.code
        price = getattr(tick, strategyCls.buyPrice)

        if accountManager is None: # 没有绑定实盘账户，则虚拟买入数量
            volume = '{0}: {1}%'.format(ratioMode, ratio)
        else:
            curCash = accountManager.curCash
            curCapital = accountManager.getCurCapital()
            if curCapital == 0: # 防止账户还没有初始化
                return None

            if ratioMode == strategyCls.cFixedCash: # 固定现金
                cash = ratio
                if cash < curCash:
                    return None
            else:
                # 计算可用资金
                cash = DyStockCtaEngineExtra._getCashByRatio(accountManager, strategyCls, ratio, ratioMode)
                cash = min(curCash, cash)

                if not strategyCls.allowSmallCashBuy:
                    # 如果剩余资金不足总资产的@allPosPreliminaryRatio%，则满仓
                    if (curCash - cash)/curCapital*100 < DyStockTradeCommon.allPosPreliminaryRatio:
                        cash = curCash

                    # 买入资金不足总资产的@allPosPreliminaryRatio%，则不买入。
                    # 防止小单买入，手续费成本高。
                    if cash/curCapital*100 < DyStockTradeCommon.allPosPreliminaryRatio:
                        return None

            # 计算股票的可买数量
            volume = DyStockTradeCommon.getBuyVol(cash, code, price)

        return ctaEngine.buy(strategyCls, tick, volume, signalInfo)

    def sellByRatio(ctaEngine, accountManager, strategy, tick, ratio, ratioMode, sellReason=None, signalInfo=None):
        """
            @strategy: 策略实例，为了获取策略的持仓。这样不会卖掉其他策略的相同持仓。
        """
        code = tick.code
        price = getattr(tick, strategy.sellPrice)

        if accountManager is None:
            volume = '{0}: {1}%'.format(ratioMode, ratio)
        else:
            # 计算需要卖多少资金
            cash = DyStockCtaEngineExtra._getCashByRatio(accountManager, strategy.__class__, ratio, ratioMode)
        
            # 计算股票需要卖的数量
            volume = DyStockTradeCommon.getSellVol(cash, code, price)

            # 计算策略的股票可卖数量
            availVol = strategy.getCodePosAvailVolume(code)
            volume = min(availVol, volume)

            # 如果股票的剩余持仓市值不足需要卖出资金的10%，则清仓这只股票
            if (strategy.getCodePosTotalVolume(code) - volume)*price / cash < 0.1:
                volume = availVol

        return ctaEngine.sell(strategy.__class__, tick, volume, sellReason, signalInfo)
