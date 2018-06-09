from .....Common.DyStockCommon import *
from ....DyStockBackTestingCommon import *
from .....Trade.DyStockTradeCommon import *
from .....Common.Ui.Basic.DyStockTableWidget import *


class DyStockBackTestingStrategyResultDealsWidget(DyStockTableWidget):

    sellReasonFGMap = {DyStockSellReason.stopLoss: Qt.darkGreen,
                       DyStockSellReason.stopLossStep: Qt.darkGreen,
                       DyStockSellReason.stopProfit: Qt.red,
                       DyStockSellReason.stopTime: QColor('#4169E1'),
                       DyStockSellReason.liquidate: QColor("#FF6100"),
                       DyStockSellReason.strategy: None,
                       }

    header = ['委托时间', '成交时间', '代码', '名称', '数量', '成交价格', '成交金额',
              '交易成本(0)', '交易类型(买入:0,卖出:0)', '盈亏(0)', '盈亏(%)', '持有期', '最大亏损比(%)',
              '除权除息', '卖出原因', '信号信息']


    def __init__(self, eventEngine, name, strategyCls):
        """
            @name: period的字符形式
        """
        self._strategyCls = strategyCls

        super().__init__(eventEngine, name=name, index=True, floatRound=3)

        self.setColNames(self.header)
        
        self._typeCol = self.header.index('交易类型(买入:0,卖出:0)')
        self._pnlCol = self.header.index('盈亏(0)')
        self._pnlRatioCol = self.header.index('盈亏(%)')
        self._minPnlRatioCol = self.header.index('最大亏损比(%)')
        self._sellReasonCol = self.header.index('卖出原因')
        self._tradeCostCol = self.header.index('交易成本(0)')

        # 定制的表头右键Actions，防止重复创建
        self.__customHeaderContextMenuActions = set()

    def customizeHeaderContextMenu(self, headerItem):
        """
            子类改写
            这样子类可以定制Header的右键菜单
        """
        super().customizeHeaderContextMenu(headerItem)

        for action in self.__customHeaderContextMenuActions:
            self._headerMenu.removeAction(action)
            del action

        if self._strategyCls.signalDetailsHeader is None or headerItem.text() != '信号信息':
            return

        action = QAction('⊕买入->卖出', self)
        action.triggered.connect(self.__copyFromBuy2SellAct)
        self._headerMenu.addAction(action)
        self.__customHeaderContextMenuActions.add(action)

        action = QAction('⊕Split', self)
        action.triggered.connect(self.__splitAct)
        self._headerMenu.addAction(action)
        self.__customHeaderContextMenuActions.add(action)

    def __copyFromBuy2SellAct(self):
        """
            将信号信息从买入交易拷贝到卖出交易，这样可以根据每笔盈亏做统计分析。
            !!!这个行为只能针对一个交易日内同一股票只买卖一次。
        """
        # get column name of trade type
        for name in self.getColNames():
            if '交易类型' in name:
                break

        rows = self.getColumnsData(['成交时间', '代码', name, '信号信息'])

        # 按时间升序排序
        sortedRows = copy.copy(rows) # only use shadow copy so that we can change element of inner list
        sortedRows.sort(key=operator.itemgetter(0))

        buyRowDict = {}
        for row in sortedRows:
            buyRows = buyRowDict.setdefault(row[1], [])

            if row[2] == '卖出':
                row[3] = buyRows[-1][3] # replace sell '信号信息' by latest buy '信号信息'
            else:
                buyRows.append(row)

        # copy to table widget
        col = self._getColPos('信号信息')
        for row in range(self.rowCount()):
            if rows[row][2] == '买入':
                continue

            item = self.item(row, col)
            if item is None:
                item = DyTableWidgetItem(self._role)
                self.setItem(row, col, item)

            # set item data
            self._setItemDataFast(item, rows[row][3])

    def __splitAct(self):
        def _toDict(info):
            dicts = {}
            if not info:
                return dicts

            fields = info.split(',')
            for field in fields:
                try:
                    key, value = field.split(':')
                except:
                    continue

                dicts[key] = value

            return dicts


        col = self._getColPos('信号信息')
        colData = []
        for row in range(self.rowCount()):
            item = self.item(row, col)

            dicts = _toDict(item.text())

            rowData = [None]*len(self._strategyCls.signalDetailsHeader)
            for i, name in enumerate(self._strategyCls.signalDetailsHeader):
                rowData[i] = dicts.get(name)

            colData.append(rowData)

        self.fastAppendColumns(self._strategyCls.signalDetailsHeader, colData)

    def append(self, deals):
        """
            添加一个交易日结束后的成交
        """
        buyCount, sellCount = 0, 0
        pnl = 0
        tradeCost = 0
        for deal in deals:
            # append into table
            row = [deal.entrustDatetime.strftime('%Y-%m-%d %H:%M:%S'), deal.datetime.strftime('%Y-%m-%d %H:%M:%S'), deal.code, deal.name,
                   deal.volume, deal.price, deal.volume*deal.price, deal.tradeCost, deal.type,
                   deal.pnl, deal.pnlRatio, deal.holdingPeriod, deal.minPnlRatio,
                   None if deal.xrd is None else '是' if deal.xrd else '否',
                   deal.sellReason, deal.signalInfo]

            rowCol = self.appendRow(row)

            tradeCost += deal.tradeCost

            # ----- 设置item -----

            # 设置'交易类型'前景色
            if deal.type == '买入':
                color = Qt.red
                buyCount += 1
            else:
                color = Qt.darkGreen
                sellCount += 1

            self.setItemForeground(rowCol, self._typeCol, color)

            # 设置'盈亏'前景色
            if deal.pnl is not None and deal.pnl != 0:
                color = Qt.red if deal.pnl > 0 else Qt.darkGreen
                self.setItemForeground(rowCol, self._pnlCol, color)

                pnl += deal.pnl

            # 设置'盈亏'前景色
            if deal.pnlRatio is not None and deal.pnlRatio != 0:
                color = Qt.red if deal.pnlRatio > 0 else Qt.darkGreen
                self.setItemForeground(rowCol, self._pnlRatioCol, color)

            # 设置'最大亏损比'前景色
            if deal.minPnlRatio is not None and deal.minPnlRatio != 0:
                color = Qt.red if deal.minPnlRatio > 0 else Qt.darkGreen
                self.setItemForeground(rowCol, self._minPnlRatioCol, color)

            # 设置'卖出原因'前景色
            color = self.sellReasonFGMap.get(deal.sellReason)
            if color is not None:
                self.setItemForeground(rowCol, self._sellReasonCol, color)

        # ----- 设置header -----

        # 设置'交易类型'
        colName = self.getColName(self._typeCol)
        buyCountStart = colName.find('买入')
        sellCountStart = colName.find('卖出')

        buyCount += int(colName[buyCountStart + 3 : sellCountStart - 1])
        sellCount += int(colName[sellCountStart + 3 : -1])

        self.setColName(self._typeCol, '交易类型(买入:{0},卖出:{1})'.format(buyCount, sellCount))

        # 设置'盈亏'
        colName = self.getColName(self._pnlCol)
        pnl += float(colName[3:-1])

        self.setColName(self._pnlCol, '盈亏(%.2f)'%pnl)

        # 设置'交易成本'
        colName = self.getColName(self._tradeCostCol)
        tradeCost += float(colName[5:-1])

        self.setColName(self._tradeCostCol, '交易成本(%.2f)'%tradeCost)

    def _getItemCodeDate(self, item):
        # get code
        row = self.row(item)
        code = self[row, '代码']
        if code is None: return None, None

        # get date
        time = self[row, '成交时间']
        date = time[:len('2000-00-00')]

        return code, date

    def _getItemCodeName(self, item):
        # get code
        row = self.row(item)
        code = self[row, '代码']
        name = self[row, '名称']
        if code is None: return None, None

        return code, name

    def getRightClickCodeDate(self):
        item = self.itemAt(self._rightClickPoint)
        if item is None: return None, None

        return self._getItemCodeDate(item)

    def getCodeDate(self, item):
        return self._getItemCodeDate(item)

    def getDateCodeList(self):
        """
            添加列将会调用此接口。对于回测来讲，主要关注买入之前的数据关系。
            所以对卖出的交易，则用买入时间代替。
        """
        # get column name of trade type
        for name in self.getColNames():
            if '交易类型' in name:
                break

        rows = self.getColumnsData(['成交时间', '代码', name])

        # 按时间升序排序
        sortedRows = copy.copy(rows) # only use shadow copy so that we can change element of inner list
        sortedRows.sort(key=operator.itemgetter(0))

        buyRowDict = {}
        for row in sortedRows:
            buyRows = buyRowDict.setdefault(row[1], [])

            if row[2] == '卖出':
                row[0] = buyRows[-1][0] # replace sell time by latest buy time
            else:
                buyRows.append(row)

        # strip to [date, code] list
        dateCodeList = [[row[0][:len('yyyy-mm-dd')], row[1]] for row in rows]

        return dateCodeList

    def getCodePriceList(self):
        return self.getColumnsData(['代码', '成交价格'])

    def getRightClickCodeName(self):
        item = self.itemAt(self._rightClickPoint)
        if item is None: return None, None

        return self._getItemCodeName(item)

    def setAllItemsForeground(self):
        # set all items foreground
        for col, colName in enumerate(self.getColNames(), 1):
            if not ('交易类型' in colName or '盈亏' in colName or '亏损' in colName or '卖出原因' in colName):
                continue

            for row in range(self.rowCount()):
                item = self.item(row, col)
                if item is None:
                    continue

                itemData = item.data(self._role)

                if '交易类型' in colName:
                    if itemData == '买入':
                        item.setForeground(Qt.red)
                    else:
                        item.setForeground(Qt.darkGreen)

                elif '盈亏' in colName or '亏损' in colName:
                    try:
                        itemData = float(itemData)

                        if itemData > 0:
                            item.setForeground(Qt.red)
                        elif itemData < 0:
                            item.setForeground(Qt.darkGreen)
                    except Exception:
                        pass

                elif '卖出原因' in colName:
                    color = self.sellReasonFGMap.get(itemData)
                    if color is not None:
                        item.setForeground(color)

    def getCustomSaveData(self):
        """
            子类改写
        """
        customData = {'class': 'DyStockBackTestingStrategyResultDealsWidget',
                      'strategyCls': self._strategyCls.name
                      }

        return customData

    def _newWindow(self, rows=None):
        """
            子类改写
        """
        window = self.__class__(self._eventEngine, self._name, self._strategyCls)

        if rows is None:
            rows = self.getAll()

        window.setColNames(self.getColNames())
        window.fastAppendRows(rows, self.getAutoForegroundColName())

        window.setAllItemsForeground()

        window.setWindowTitle('成交明细-{0}{1}'.format(self._strategyCls.chName, self._name))
        window.showMaximized()

        self._windows.append(window)

    def getUniqueName(self):
        """
            子类改写
        """
        return '{0}_{1}'.format(self._strategyCls.chName, self._name)

    def _itemDoubleClicked(self, item):
        # get code
        code, baseDate = self.getCodeDate(item)
        if code is None or baseDate is None:
            return

        # get column name of trade type
        for name in self.getColNames():
            if '交易类型' in name:
                break

        rows = self.getColumnsData(['成交时间', '代码', name])

        # filter by code
        buySellDates = {}
        for time_, code_, type_ in rows:
            if code == code_:
                date_ = time_[:len('2000-00-00')]
                buySellDates[date_] = type_

        self._dataViewer.plotBuySellDayCandleStick(code, buySellDates)
