import numpy as np


DyTalibExpAdjust = True # pandas默认是True，同花顺默认是False。True时，最近的值权重会大些。数据足够多的时候，趋向一致。


def WMA(X, W, N):
    """
        加权移动平均值
        @X: 观察值序列
        @W: 权重序列
        @N: 周期
    """
    assert len(X) == len(W)

    # init
    weightedX = [np.nan]*len(X)

    # calculate first weighted x
    numerator, denominator = 0, 0
    for x, w in zip(X[:N], W[:N]):
        numerator += x*w
        denominator += w

    if len(X) >= N:
        weightedX[N-1] = numerator/denominator

    # WMA
    for i in range(N, len(X)):
        numerator = numerator + X[i]*W[i] - X[i-N]*W[i-N]
        denominator = denominator + W[i] - W[i-N]

        weightedX[i] = numerator/denominator

    return weightedX

def EWMA(X, alpha, adjust=DyTalibExpAdjust):
    """
        指数加权移动平均值
        数据长度10000以下时，比pandas要快
        @X: numpy array or list
        @alpha: 平滑指数
        @adjust: pandas里默认是True，这里默认是False跟同花顺保持一致。True时最近的权重会大些。
        @return: list
    """
    weightedX = [0]*len(X)
    weightedX[0] = X[0]

    if adjust:
        numerator = X[0]
        denominator = 1

        for i in range(1, len(X)):
            numerator = X[i] + numerator*(1-alpha)
            denominator = 1 + denominator*(1-alpha)

            weightedX[i] = numerator/denominator
    else:
        for i in range(1, len(X)):
            weightedX[i] = alpha*X[i] + (1-alpha)*weightedX[i-1]

    return weightedX

def EMA(X, N, adjust=DyTalibExpAdjust):
    """
        同花顺的EMA
        数据长度5000以下时，比pandas要快
        @X: numpy array or list
        @N: 周期
        @adjust: pandas里默认是True，这里默认是False跟同花顺保持一致。True时，最近的值权重会大些。
        @return: list
    """
    alpha = 2/(N + 1)

    return EWMA(X, alpha, adjust=adjust)

def SMA(C, N, M, adjust=DyTalibExpAdjust):
    """
        同花顺的SMA
        N > M
    """
    alpha = M/N

    return EWMA(C, alpha, adjust=adjust)

def RSI(closes, timeperiod=12, adjust=DyTalibExpAdjust):
    """
        同花顺公式：
            LC := REF(CLOSE,1);
            SMA(MAX(CLOSE-LC,0),N,1)/SMA(ABS(CLOSE-LC),N,1)*100;

        @closes: numpy array or list
        @return: list，前@timeperiod个元素的值是NaN。主要因为计算差值多占用了一个元素。
    """
    # calculate (ΔP+) and (ΔP+) + |ΔP-|
    up = [0]*(len(closes) - 1)
    absUpDown = [0]*(len(closes) - 1)
    for i in range(1, len(closes)):
        diff = closes[i] - closes[i-1]
        if diff > 0:
            up[i-1] = diff

        absUpDown[i-1] = abs(diff)

    # SMA
    smaUp = SMA(up, timeperiod, 1, adjust=adjust)
    smaAbsUpDown = SMA(absUpDown, timeperiod, 1, adjust=adjust)

    # RSI
    rsi = [np.nan]*len(closes)
    for i in range(timeperiod, len(closes)):
        rsi[i] = smaUp[i-1]/smaAbsUpDown[i-1]*100

    return rsi

def ATR(highs, lows, closes, timeperiod=14, adjust=DyTalibExpAdjust):
    """
        @return: list，前@timeperiod个元素的值是NaN。主要因为计算差值多占用了一个元素。
    """
    assert len(highs) == len(lows) == len(closes)

    trs = [0]*(len(highs) - 1)
    for i in range(1, len(highs)):
        tr = max(highs[i], closes[i-1]) - min(lows[i], closes[i-1])
        trs[i-1] = tr

    atr = EMA(trs, timeperiod, adjust=adjust)

    atr.insert(0, np.nan)
    atr[:timeperiod] = [np.nan]*timeperiod

    return atr

def WATR(highs, lows, closes, W, timeperiod=14):
    """
        加权ATR
        @W: 权重序列
        @return: list，前@timeperiod个元素的值是NaN。主要因为计算差值多占用了一个元素。
    """
    assert len(highs) == len(lows) == len(closes) == len(W)

    trs = [0]*(len(highs) - 1)
    for i in range(1, len(highs)):
        tr = max(highs[i], closes[i-1]) - min(lows[i], closes[i-1])
        trs[i-1] = tr

    atr = WMA(trs, W[1:], timeperiod)

    atr.insert(0, np.nan)

    return atr