from PyQt5.QtWidgets import QDialog, QGridLayout, QLabel, QLineEdit, QPushButton, QApplication, QTextEdit, QMessageBox
from PyQt5 import QtCore

from Stock.Common.DyStockCommon import *
from EventEngine.DyEvent import *
from DyCommon.Ui.DyTableWidget import *
from ..Ind.Account.DyStockTradeStrategyPosWidget import *


class DyStockTradeStrategyPosSellWidget(DyStockTradeStrategyPosWidget):
    def __init__(self, parent, eventEngine, strategyCls):
        super().__init__(eventEngine, strategyCls)

        self._parent = parent

        self.itemDoubleClicked.connect(self._itemDoubleClicked)

    def _itemDoubleClicked(self, item):
        row = item.row()
        
        code = self[row, '代码']
        price = self[row, '现价(元)']

        self._parent.setSellCodePrice(code, price)


class DyStockTradeStrategySellDlg(QDialog):

    stockMarketTicksSignal = QtCore.pyqtSignal(type(DyEvent()))
    stockStrategyPosAckSignal = QtCore.pyqtSignal(type(DyEvent()))
    stockStrategyPosUpdateSignal = QtCore.pyqtSignal(type(DyEvent()))

    def __init__(self, eventEngine, strategyCls):
        super().__init__()

        self._eventEngine = eventEngine
        self._strategyCls = strategyCls

        self._code = None # current stock code
        self._tick = None # current tick of @self._code
        self._curPos = None # 策略持仓字典

        self._initUi()

        self._registerEvent()

        self._init()

    def _init(self):
        event = DyEvent(DyEventType.stockStrategyPosReq)
        event.data = self._strategyCls

        self._eventEngine.put(event)

    def _initUi(self):
        self.setWindowTitle(self._strategyCls.chName)
        
        # 策略持仓
        posLabel = QLabel('策略持仓')
        posLabel.setStyleSheet("color:#4169E1")

        self._posWidget = DyStockTradeStrategyPosSellWidget(self, self._eventEngine, self._strategyCls)

        # 卖出
        sellCodeLabel = QLabel('股票代码')
        sellCodeLabel.setStyleSheet("color:#4169E1")
        self._sellCodeLineEdit = QLineEdit()

        sellVolumeLabel = QLabel('数量(手)')
        sellVolumeLabel.setStyleSheet("color:#4169E1")
        self._sellVolumeLineEdit = QLineEdit('1')

        sellPriceLabel = QLabel('价格(元)')
        sellPriceLabel.setStyleSheet("color:#4169E1")
        self._sellPriceLineEdit = QLineEdit()

        # 行情
        self._codeLabel = QLabel('股票代码')
        self._nameLabel = QLabel('股票名称')
        self._priceLabel = QLabel('股票现价')
        self._increaseLabel = QLabel('涨幅(%):')

        self._bidAskTable = DyTableWidget(readOnly=True, index=False, floatRound=3)
        self._bidAskTable.setColNames([None, '价格(元)', '数量(手)'])
        self._bidAskTable.fastAppendRows([
                                            ['卖5', None, None],
                                            ['卖4', None, None],
                                            ['卖3', None, None],
                                            ['卖2', None, None],
                                            ['卖1', None, None],
                                            [None, None, None],
                                            ['买1', None, None],
                                            ['买2', None, None],
                                            ['买3', None, None],
                                            ['买4', None, None],
                                            ['买5', None, None]
                                        ])

        cancelPushButton = QPushButton('Cancel')
        okPushButton = QPushButton('卖出')
        cancelPushButton.clicked.connect(self._cancel)
        okPushButton.clicked.connect(self._ok)

        # 布局
        grid = QGridLayout()
        grid.setSpacing(10)
 
        grid.addWidget(posLabel, 0, 0)
        grid.addWidget(self._posWidget, 1, 0, 10, 10)

        start = 12

        grid.addWidget(sellCodeLabel, start + 0, 0)
        grid.addWidget(self._sellCodeLineEdit, start + 1, 0)
        grid.addWidget(sellVolumeLabel, start + 2, 0)
        grid.addWidget(self._sellVolumeLineEdit, start + 3, 0)
        grid.addWidget(sellPriceLabel, start + 4, 0)
        grid.addWidget(self._sellPriceLineEdit, start + 5, 0)

        grid.addWidget(self._codeLabel, start + 0, 1, 1, 10)
        grid.addWidget(self._nameLabel, start + 1, 1)
        grid.addWidget(self._priceLabel, start + 2, 1)
        grid.addWidget(self._increaseLabel, start + 3, 1)
        grid.addWidget(self._bidAskTable, start + 4, 1, 30, 10)

        grid.addWidget(okPushButton, start + 6, 0)
        grid.addWidget(cancelPushButton, start + 7, 0)
 
 
        self.setLayout(grid)
        self.setMinimumWidth(QApplication.desktop().size().width()//3)


        self._sellCodeLineEdit.textChanged.connect(self._sellCodeChanged)

    def _ok(self):
        try:
            if self._codeLabel.text() != self._tick.code:
                QMessageBox.warning(self, '错误', '没有指定代码的Tick数据!')
                return
        except Exception:
            QMessageBox.warning(self, '错误', '没有指定代码的Tick数据!')
            return

        event = DyEvent(DyEventType.stockStrategyManualSell)
        event.data['class'] = self._strategyCls
        event.data['tick'] = self._tick
        event.data['volume'] = float(self._sellVolumeLineEdit.text()) * 100

        # 不指定价格，则根据tick买入
        price = self._sellPriceLineEdit.text()
        event.data['price'] = float(price) if price else None

        self._eventEngine.put(event)

        self._unregisterEvent()

        self._posWidget.close()
        self.accept()

    def _cancel(self):
        self._unregisterEvent()

        self._posWidget.close()
        self.reject()

    def setSellCodePrice(self, code, price):
        self._sellCodeLineEdit.setText(code[:6])
        self._sellPriceLineEdit.setText(str(price))

    def _getInputCode(self):
        if not self._curPos:
            return None

        code = self._sellCodeLineEdit.text()
        if len(code) != 6:
            return None

        code = DyStockCommon.getDyStockCode(code)
        if code not in self._curPos:
            return None

        return code

    def _sellCodeChanged(self):
        self._code = self._getInputCode()
        if self._code is None:
            self._codeLabel.setText('输入代码在策略持仓里不存在!')
            return

        self._codeLabel.setText(self._code)
        
    def _stockStrategyPosAckSignalEmitWrapper(self, event):
        self.stockStrategyPosAckSignal.emit(event)

    def _stockMarketTicksSignalEmitWrapper(self, event):
        self.stockMarketTicksSignal.emit(event)

    def _stockStrategyPosUpdateSignalEmitWrapper(self, event):
        self.stockStrategyPosUpdateSignal.emit(event)

    def _registerEvent(self):
        self.stockMarketTicksSignal.connect(self._stockMarketTicksHandler)
        self._eventEngine.register(DyEventType.stockMarketTicks, self._stockMarketTicksSignalEmitWrapper)

        self.stockStrategyPosAckSignal.connect(self._stockStrategyPosAckHandler)
        self._eventEngine.register(DyEventType.stockStrategyPosAck, self._stockStrategyPosAckSignalEmitWrapper)

        self.stockStrategyPosUpdateSignal.connect(self._stockStrategyPosUpdateHandler)
        self._eventEngine.register(DyEventType.stockStrategyPosUpdate + self._strategyCls.name, self._stockStrategyPosUpdateSignalEmitWrapper)

    def _unregisterEvent(self):
        self.stockMarketTicksSignal.disconnect(self._stockMarketTicksHandler)
        self._eventEngine.unregister(DyEventType.stockMarketTicks, self._stockMarketTicksSignalEmitWrapper)

        self.stockStrategyPosAckSignal.disconnect(self._stockStrategyPosAckHandler)
        self._eventEngine.unregister(DyEventType.stockStrategyPosAck, self._stockStrategyPosAckSignalEmitWrapper)

        self.stockStrategyPosUpdateSignal.disconnect(self._stockStrategyPosUpdateHandler)
        self._eventEngine.unregister(DyEventType.stockStrategyPosUpdate + self._strategyCls.name, self._stockStrategyPosUpdateSignalEmitWrapper)

    def _stockStrategyPosAckHandler(self, event):
        self._curPos = event.data

        self._posWidget.update(event.data)

    def _stockStrategyPosUpdateHandler(self, event):
        self._curPos = event.data

        self._posWidget.update(event.data)

    def _stockMarketTicksHandler(self, event):
        ticks = event.data

        self._tick = ticks.get(self._code)
        if self._tick is None:
            return

        tick = self._tick

        self._codeLabel.setText(tick.code)
        self._nameLabel.setText(tick.name)

        self._priceLabel.setText(str(tick.price))
        if tick.price > tick.preClose:
            self._priceLabel.setStyleSheet("color:red")
        elif tick.price < tick.preClose:
            self._priceLabel.setStyleSheet("color:darkgreen")

        increase = round((tick.price - tick.preClose)/tick.preClose*100, 2)
        self._increaseLabel.setText('涨幅(%): {0}%'.format(increase))
        if increase > 0:
            self._increaseLabel.setStyleSheet("color:red")
        elif increase < 0:
            self._increaseLabel.setStyleSheet("color:darkgreen")

        self._bidAskTable.fastAppendRows([
                                            ['卖5', tick.askPrices[4], round(tick.askVolumes[4]/100)],
                                            ['卖4', tick.askPrices[3], round(tick.askVolumes[3]/100)],
                                            ['卖3', tick.askPrices[2], round(tick.askVolumes[2]/100)],
                                            ['卖2', tick.askPrices[1], round(tick.askVolumes[1]/100)],
                                            ['卖1', tick.askPrices[0], round(tick.askVolumes[0]/100)],
                                            [None, tick.price, None],
                                            ['买1', tick.bidPrices[0], round(tick.bidVolumes[0]/100)],
                                            ['买2', tick.bidPrices[1], round(tick.bidVolumes[1]/100)],
                                            ['买3', tick.bidPrices[2], round(tick.bidVolumes[2]/100)],
                                            ['买4', tick.bidPrices[3], round(tick.bidVolumes[3]/100)],
                                            ['买5', tick.bidPrices[4], round(tick.bidVolumes[4]/100)]
                                        ], new=True)

