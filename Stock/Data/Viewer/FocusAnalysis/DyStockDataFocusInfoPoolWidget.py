from ....Common.DyStockCommon import *
from ....Common.Ui.Basic.DyStockTableWidget import *


class DyStockDataFocusInfoPoolWidget(DyStockTableWidget):
    """ focus info pool widget """

    header = ['热点', # 若一只股票有多个热点，只取强度最大的作为其热点
              '热点强度', # 此热点在市场中的强度
              '热点涨幅(%)', # 被此热点追踪到的股票的平均涨幅
              '热点涨停数',
              '热点涨停数占比(%)',
              '热点股票数',
              '龙头涨幅(%)', # 龙一，龙二，龙三的平均涨幅
              '龙一',
              '龙二',
              '龙三',
              ]

    def __init__(self, dataViewer, date, focusInfoPool):
        super().__init__(dataViewer.eventEngine,
                         name='热点',
                         baseDate=date
                         )
        self._focusInfoPool = focusInfoPool

        self._dragonsMap = {} # {name: code}

        self._initUi()

    def _getDragons(self, focusInfo):
        data = [None]*3
        for i, (code, name) in enumerate(focusInfo.dragons):
            data[i] = name
            self._dragonsMap[name] = code

        return data

    def _initUi(self):
        self.setWindowTitle('热点[{0}]'.format(self._baseDate))

        self.setColNames(self.header)

        rows = []
        focusList = sorted(self._focusInfoPool, key=lambda k: self._focusInfoPool[k].strength, reverse=True)
        for focus in focusList:
            focusInfo = self._focusInfoPool[focus]

            row = [focus,
                   focusInfo.strength,
                   focusInfo.increase,
                   focusInfo.limitUpNbr,
                   focusInfo.limitUpNbr/len(focusInfo.codes)*100,
                   len(focusInfo.codes),
                   focusInfo.dragonIncrease,
                   ]

            row.extend(self._getDragons(focusInfo))

            rows.append(row)

        self.fastAppendRows(rows, '热点涨幅(%)')

    #---------------------------------------------- 由子类根据自己的Table格式改写 ----------------------------------------------
    def getDateCodeList(self):
        return None

    def getCodeList(self):
        return None

    def getCodePriceList(self):
        return None

    def getRightClickCodeDate(self):
        item = self.itemAt(self._rightClickPoint)
        if item is None:
            return None, None

        code = self._dragonsMap.get(item.text())
        if code is None:
            return None, None

        return code, self._baseDate

    def getRightClickCodeName(self):
        item = self.itemAt(self._rightClickPoint)
        if item is None:
            return None, None

        name = item.text()
        code = self._dragonsMap.get(name)
        if code is None:
            return None, None

        return code, name

    def getCodeDate(self, item):
        code = self._dragonsMap.get(item.text())
        if code is None:
            return None, None

        return code, self._baseDate
