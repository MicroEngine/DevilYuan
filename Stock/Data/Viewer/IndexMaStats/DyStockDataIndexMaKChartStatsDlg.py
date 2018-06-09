from datetime import *

from PyQt5.QtWidgets import QDialog, QGridLayout, QLabel, QLineEdit, QPushButton, QRadioButton, QButtonGroup, QCheckBox, QWidget, QTabWidget

from ....Common.DyStockCommon import *


class DyStockDataIndexMaKChartStatsIndicatorWidget(QWidget):

    def __init__(self, mas=[5, 10, 20, 30, 60, 120]):
        """
            @mas: [5, 10, 20, 30, 60, 120]
        """
        super().__init__()

        indPeriodLabel = QLabel('指标周期')
        indMaLabel = QLabel('指标均线(格式: 5,10。空即无均线）')

        self._checkBoxes = []
        self._lineEdits = []
        for ma in mas:
            self._checkBoxes.append(QCheckBox('%d日'%ma))
            self._lineEdits.append(QLineEdit())

        # 布局
        grid = QGridLayout()
        grid.setSpacing(10)
 
        grid.addWidget(indPeriodLabel, 0, 0)
        grid.addWidget(indMaLabel, 0, 1)

        for i, (checkBox, lineEdit) in enumerate(zip(self._checkBoxes, self._lineEdits), 1):
            grid.addWidget(checkBox, i, 0)
            grid.addWidget(lineEdit, i, 1)

        self.setLayout(grid)

    def get(self):
        """
            @return: {5: [5,10], 10: []}
        """
        values = {}
        for checkBox, lineEdit in zip(self._checkBoxes, self._lineEdits):
            if checkBox.isChecked():
                period = int(checkBox.text()[:-1])
                periodMa = [int(x) for x in lineEdit.text().split(',') if lineEdit.text()]

                values[period] = periodMa

        return values


class DyStockDataIndexMaKChartStatsIndicatorTabWidget(QTabWidget):

    def __init__(self):
        super().__init__()

        self._priceMaWidget = DyStockDataIndexMaKChartStatsIndicatorWidget()
        self.addTab(self._priceMaWidget, '价格均线')

        self._volumeMaWidget = DyStockDataIndexMaKChartStatsIndicatorWidget()
        self.addTab(self._volumeMaWidget, '量能均线')

        self._priceMaDiffWidget = DyStockDataIndexMaKChartStatsIndicatorWidget()
        self.addTab(self._priceMaDiffWidget, '价格均线离差')

    def get(self):
        values = {}

        values['ma'] = self._priceMaWidget.get()
        values['vma'] = self._volumeMaWidget.get()
        values['dma'] = self._priceMaDiffWidget.get()

        return values


class DyStockDataIndexMaKChartStatsDlg(QDialog):

    def __init__(self, data, parent=None):
        super().__init__(parent)

        self._data = data

        self._initUi()

    def _initUi(self):
        self.setWindowTitle('指数均线K线图示指标')

        self._indicatorWidget = DyStockDataIndexMaKChartStatsIndicatorTabWidget()

        cancelPushButton = QPushButton('Cancel')
        okPushButton = QPushButton('OK')
        cancelPushButton.clicked.connect(self._cancel)
        okPushButton.clicked.connect(self._ok)

        # 布局
        grid = QGridLayout()
        grid.setSpacing(10)
 
        grid.addWidget(self._indicatorWidget, 0, 0, 1, 2)

        grid.addWidget(okPushButton, 1, 1)
        grid.addWidget(cancelPushButton, 1, 0)
 
        self.setLayout(grid)

    def _ok(self):
        self._data.update(**self._indicatorWidget.get())

        self.accept()

    def _cancel(self):
        self.reject()
