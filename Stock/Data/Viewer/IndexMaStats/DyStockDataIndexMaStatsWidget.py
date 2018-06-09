from PyQt5.QtGui import QColor

from DyCommon.Ui.DyStatsDataFrameTableWidget import *


class DyStockDataIndexMaStatsWidget(DyStatsDataFrameTableWidget):
    """ 指数均线统计窗口，并提示操作建议 """

    def __init__(self, indexCode, indexName, df, parent=None):

        # 预测操作
        df = self._predict(df)

        # change index to string
        df.index = df.index.map(lambda x: x.strftime('%Y-%m-%d'))

        # change index to column
        df.reset_index(inplace=True)
        df.rename(columns={'index':'日期'}, inplace=True)

        super().__init__(df, parent)

        self._indexCode = indexCode
        self._indexName = indexName

        # set color
        self._setColor()

    def _setColor(self):
        shortOpCol = self._getColPos('短线操作')
        middleOpCol = self._getColPos('中线操作')

        opCols = []
        if shortOpCol is not None: opCols.append(shortOpCol)
        if middleOpCol is not None: opCols.append(middleOpCol)
        if not opCols: return

        maRange = [self._getColPos('ma5'), self._getColPos('ma120') + 1]
        maDeltaRange = [self._getColPos('ma5Δ'), self._getColPos('ma120Δ') + 1]

        dmaRange = [self._getColPos('dma5'), self._getColPos('dma120') + 1]
        dmaDeltaRange = [self._getColPos('dma5Δ'), self._getColPos('dma120Δ') + 1]

        for row in range(self.rowCount()):
            # 设置日期前景色
            self.setItemForeground(row, 0, QColor('#FF6100'))

            # 设置操作前景色
            for opCol in opCols:
                data = self[row, opCol]
                if not isinstance(data, str): continue

                if  '买入' in data:
                    self.setItemForeground(row, opCol, Qt.red)
                elif '卖出' in data:
                    self.setItemForeground(row, opCol, Qt.darkGreen)

            # 设置收盘价均线统计前景色
            for col in range(*maRange):
                self.setItemForeground(row, col, QColor('#4169E1'))

            for col in range(*maDeltaRange):
                self.setItemForeground(row, col, QColor('#4169E1'))

            # 设置离差收盘价均线比统计前景色
            for col in range(*dmaRange):
                self.setItemForeground(row, col, QColor('#A020F0'))

            for col in range(*dmaDeltaRange):
                self.setItemForeground(row, col, QColor('#A020F0'))

    def _predict(self, df):

        pctChangeDf = df.pct_change()
        pctChangeDf.rename(columns={x: (x+'Δ') for x in df.columns}, inplace=True)

        newDf = pd.concat([df, pctChangeDf], axis=1)


        ############### 短线操作 ###############

        # buy
        shortBuyDf = newDf[(newDf['ma5'] >= 10) & (newDf['ma5'] < 20)]
        shortBuyDf = shortBuyDf[shortBuyDf['ma5Δ'] + shortBuyDf['ma60Δ'] > -1]
        shortBuyMinusSeries = pd.Series(index=shortBuyDf.index, data=['买入-']*shortBuyDf.shape[0], name='短线操作')

        shortBuyDf = newDf[newDf['ma5'] < 10]
        shortBuyDf = shortBuyDf[shortBuyDf['ma5Δ'] + shortBuyDf['ma60Δ'] > -1]
        shortBuySeries = pd.Series(index=shortBuyDf.index, data=['买入']*shortBuyDf.shape[0], name='短线操作')

        # sell
        shortSellDf = newDf[newDf['ma5'] > 80]
        shortSellDf = shortSellDf[(shortSellDf['ma5Δ'] + shortSellDf['ma10Δ'] < 1) & (shortSellDf['ma60Δ'] + shortSellDf['ma30Δ'] < 1)]
        shortSellSeries = pd.Series(index=shortSellDf.index, data=['卖出']*shortSellDf.shape[0], name='短线操作')

        # concat
        shortSeries = pd.concat([shortBuyMinusSeries, shortBuySeries, shortSellSeries])


        ############### 中线操作 ###############

        # buy
        middleBuyDf = newDf[newDf['ma5'] > 60]
        middleBuyDf = middleBuyDf[middleBuyDf['ma60Δ'] > 1]
        middleBuySeries = pd.Series(index=middleBuyDf.index, data=['买入']*middleBuyDf.shape[0], name='中线操作')

        # sell
        middleSellDf = newDf[newDf['ma5'] < 10]
        middleSellDf = middleSellDf[newDf['ma60'] > newDf['ma30']*1.382] # 黄金分割: 0.618
        #middleSellDf = middleSellDf[newDf['ma60'] + newDf['ma30'] > 20] # 相对高位跳杀才中线卖出，防止超卖
        middleSellDf = middleSellDf[middleSellDf['ma60Δ'] + middleSellDf['ma30Δ'] < -1]
        middleSellSeries = pd.Series(index=middleSellDf.index, data=['卖出']*middleSellDf.shape[0], name='中线操作')

        # concat
        middleSeries = pd.concat([middleBuySeries, middleSellSeries])

        # concat to DF
        df = pd.concat([df, shortSeries, middleSeries, pctChangeDf], axis=1)

        return df