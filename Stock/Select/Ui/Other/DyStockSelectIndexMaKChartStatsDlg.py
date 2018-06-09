from datetime import *

from PyQt5.QtWidgets import QDialog, QGridLayout, QLabel, QLineEdit, QPushButton, QRadioButton, QButtonGroup

from ....Common.DyStockCommon import *


class DyStockSelectIndexMaKChartStatsDlg(QDialog):

    def __init__(self, data, parent=None):
        super().__init__(parent)

        self._data = data

        self._initUi()

    def _initUi(self):
        self.setWindowTitle('指数均线K线图统计')
 
        # 控件
        startDateLable = QLabel('开始日期')
        self._startDateLineEdit = QLineEdit(datetime.now().strftime("%Y-%m-%d"))

        endDateLable = QLabel('结束日期')
        self._endDateLineEdit = QLineEdit(datetime.now().strftime("%Y-%m-%d"))

        # 指数和股票代码
        shIndexRadioButton = QRadioButton('上证指数'); shIndexRadioButton.setChecked(True)
        szIndexRadioButton = QRadioButton('深证成指')
        cybIndexRadioButton = QRadioButton('创业板指')
        zxbIndexRadioButton = QRadioButton('中小板指')

        hs300IndexRadioButton = QRadioButton('沪深300')
        zz500IndexRadioButton = QRadioButton('中证500')

        # 添加到QButtonGroup
        self._stocksButtonGroup = QButtonGroup()
        self._stocksButtonGroup.addButton(shIndexRadioButton, 1); 
        self._stocksButtonGroup.addButton(szIndexRadioButton, 2)
        self._stocksButtonGroup.addButton(cybIndexRadioButton, 3)
        self._stocksButtonGroup.addButton(zxbIndexRadioButton, 4)

        self._stocksButtonGroup.addButton(hs300IndexRadioButton, 4)
        self._stocksButtonGroup.addButton(zz500IndexRadioButton, 4)

        cancelPushButton = QPushButton('Cancel')
        okPushButton = QPushButton('OK')
        cancelPushButton.clicked.connect(self._cancel)
        okPushButton.clicked.connect(self._ok)

        # 布局
        grid = QGridLayout()
        grid.setSpacing(10)
 
        grid.addWidget(startDateLable, 0, 0)
        grid.addWidget(self._startDateLineEdit, 1, 0)

        grid.addWidget(endDateLable, 0, 1)
        grid.addWidget(self._endDateLineEdit, 1, 1)

        grid.addWidget(shIndexRadioButton, 2, 0)
        grid.addWidget(szIndexRadioButton, 2, 1)
        grid.addWidget(cybIndexRadioButton, 3, 0)
        grid.addWidget(zxbIndexRadioButton, 3, 1)

        grid.addWidget(hs300IndexRadioButton, 4, 0)
        grid.addWidget(zz500IndexRadioButton, 4, 1)

        grid.addWidget(okPushButton, 5, 1)
        grid.addWidget(cancelPushButton, 5, 0)
 
        self.setLayout(grid)

    def _getStockCode(self):
        checkedButton = self._stocksButtonGroup.checkedButton()
        text = checkedButton.text()

        return DyStockCommon.getIndexSectorByName(text)

    def _ok(self):
        self._data['startDate'] = self._startDateLineEdit.text()
        self._data['endDate'] = self._endDateLineEdit.text()
        self._data['index'] = self._getStockCode()

        self.accept()

    def _cancel(self):
        self.reject()
