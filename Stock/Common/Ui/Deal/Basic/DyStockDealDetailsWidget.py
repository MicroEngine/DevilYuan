
from DyCommon.Ui.DyStatsTableWidget import *


class DyStockDealDetailsWidget(DyStatsTableWidget):

    colNames = ['时间', '价格', '成交量(手)', '类型']

    def __init__(self, dataEngine):
        super().__init__(None, True, False, autoScroll=False)

        self._ticksEngine = dataEngine.ticksEngine
        self._daysEngine = dataEngine.daysEngine

        self.setColNames(self.colNames + ['换手(万分之)'])

    def setInfoWidget(self, widget):
        self._infoWidget = widget

    def set(self, code, date, n = 0):
        date = self._daysEngine.codeTDayOffset(code, date, n)
        if date is None: return

        self._code = code
        self._day = date

        if not self._ticksEngine.loadCode(code, date):
            return

        df = self._ticksEngine.getDataFrame(code)

        self._set(df)

    def getForegroundOverride(self, value):
        
        if value == '买盘':
            color = Qt.red
        elif value == '卖盘':
            color = Qt.darkGreen
        else:
            color = None
            
        return color

    def _set(self, df):

        df.drop('amount', axis=1, inplace=True)

        df.reset_index(inplace=True) # 把时间索引转成列
        df[['datetime']] = df['datetime'].map(lambda x: x.strftime('%H:%M:%S'))

        df.rename(columns={'datetime':'时间', 'price':'价格', 'volume':'成交量(手)', 'type':'类型'}, inplace=True)
        df.reindex(columns=self.colNames, copy=False)

        # 计算每笔的换手率
        volumeSeries = df['成交量(手)']
        volumeSum = volumeSeries.sum()
        df['换手(万分之)'] = volumeSeries * ((self._infoWidget.turn*100)/volumeSum)

        rows = df.values.tolist()

        self.fastAppendRows(rows, '类型', True)

    def forward(self):
        self.set(self._code, self._day, -1)

    def backward(self):
        self.set(self._code, self._day, 1)
