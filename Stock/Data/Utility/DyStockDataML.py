from sklearn import linear_model
from statsmodels.tsa import stattools
import statsmodels.api as sm

from .DyStockDataUtility import *


class DyStockDataML(object):
    """ 股票数据的机器学习类 """
    
    def predictReboundVol(df, w=4):
        """
            amount = rebound increase pct + previous decrease pct
        """
        extremas, peaks, bottoms = DyStockDataUtility.swings(df, w=w)

        # price of swings
        peakPrices = df.ix[peaks.index, 'high']
        peakPrices.name = 'price'

        bottomPrices = df.ix[bottoms.index, 'low']
        bottomPrices.name = 'price'

        swingPrices = pd.concat([peakPrices, bottomPrices])
        swingPrices = swingPrices.sort_index()

        # decrease and increase of point
        swingPricesPct = swingPrices.pct_change()*100

        bottomDescrease = swingPricesPct
        bottomDescrease.name = 'decrease'

        bottomIncrease = swingPricesPct.shift(-1)
        bottomIncrease.name = 'increase'

        # bottom equation
        bottomDescrease = bottomDescrease.ix[bottoms.index]
        bottomIncrease = bottomIncrease.ix[bottoms.index]
        bottomAmount = df.ix[bottoms.index, 'amt']
        bottomAmount.name = 'amount'

        bottomEquation = pd.concat([bottomAmount, bottomDescrease, bottomIncrease], axis=1)
        bottomEquation.dropna(inplace=True)

        # 线性回归
        regr = linear_model.LinearRegression()
        regr.fit(bottomEquation[['decrease', 'increase']], bottomEquation['amount'])

        # predict
        predictOutcome = regr.predict([[-7, 3]])

        return predictOutcome

    def adfTest(s):
        """
            ADF Test
            p值越大：随机漫步，可能是趋势
            p值越小：均值回归
        """
        result = stattools.adfuller(s, 1)

        return result[1]

    def trendChannel(df, w=4):
        """
            生成趋势通道
        """
        def _ols(Y, X):
            X = sm.add_constant(X)
            results = sm.OLS(Y, X).fit()
            intercept, slope = results.params

            return intercept, slope, results.rsquared

        # get swing
        extremas, peaks, bottoms = DyStockDataUtility.swings(df, w=w)

        # get x-coordinates
        peaksX = [extremas.index.get_loc(i) for i in peaks.index]

        # find the best trend channel
        if len(extremas) < 6:
            return None, None

        # from time latest to oldest
        xRange = list(range(len(extremas)))
        i = -6
        trendChannelUp, trendChannelDown = None, None # [intercept, slope]
        trendChannelUpX, trendChannelDownX = None, None
        while i > -len(extremas):
            peaksX_, bottomsX_ = [], []
            for x in xRange[i:]:
                if x in peaksX:
                    peaksX_.append(x)
                else:
                    bottomsX_.append(x)

            # 线性回归, Y = aX + b
            interceptPeak, slopePeak, rSquaredPeak = _ols(extremas.values[peaksX_], np.array(peaksX_))
            interceptBottom, slopeBottom, rSquaredBottom = _ols(extremas.values[bottomsX_], np.array(bottomsX_))

            if rSquaredPeak >= 0.8**2 and rSquaredBottom >= 0.8**2:
                if trendChannelUp is None or \
                    abs(slopePeak - slopeBottom) <= abs(trendChannelUp[1] - trendChannelDown[1]): # 上下轨越平行越好
                    trendChannelUp = [interceptPeak, slopePeak]
                    trendChannelDown = [interceptBottom, slopeBottom]

                    trendChannelUpX, trendChannelDownX = peaksX_, bottomsX_

            i -= 2 # one peak and bottom

        if trendChannelUp is None:
            return None, None

        # get 2 points each trend channel up line and down line by regression line
        # up of channel
        trendChannelUp1Time = extremas.index[trendChannelUpX[0]]
        trendChannelUp1Price = trendChannelUp[1]*trendChannelUpX[0] + trendChannelUp[0]

        trendChannelUp2Time = extremas.index[trendChannelUpX[-1]]
        trendChannelUp2Price = trendChannelUp[1]*trendChannelUpX[-1] + trendChannelUp[0]

        trendChannelUpS = pd.Series([trendChannelUp1Price, trendChannelUp2Price], index=[trendChannelUp1Time, trendChannelUp2Time])

        # down of channel
        trendChannelDown1Time = extremas.index[trendChannelDownX[0]]
        trendChannelDown1Price = trendChannelDown[1]*trendChannelDownX[0] + trendChannelDown[0]

        trendChannelDown2Time = extremas.index[trendChannelDownX[-1]]
        trendChannelDown2Price = trendChannelDown[1]*trendChannelDownX[-1] + trendChannelDown[0]

        trendChannelDownS = pd.Series([trendChannelDown1Price, trendChannelDown2Price], index=[trendChannelDown1Time, trendChannelDown2Time])

        return trendChannelUpS, trendChannelDownS