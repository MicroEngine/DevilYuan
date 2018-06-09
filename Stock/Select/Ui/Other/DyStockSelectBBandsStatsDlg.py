from datetime import *

from PyQt5.QtWidgets import QDialog, QGridLayout, QLabel, QLineEdit, QPushButton, QRadioButton, QButtonGroup

from ....Common.DyStockCommon import *


class DyStockSelectBBandsStatsDlg(QDialog):

    def __init__(self, data, parent=None):
        super(DyStockSelectBBandsStatsDlg, self).__init__(parent)

        self._data = data

        self._initUi()

        self._stocksButtonGroup.buttonClicked.connect(self._radioButtonClicked)

    def _initUi(self):
        self.setWindowTitle('股票代码')
 
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

        stockRadioButton = QRadioButton('股票代码')
        self._stockLineEdit = QLineEdit(); self._stockLineEdit.setEnabled(False)

        # 添加到QButtonGroup
        self._stocksButtonGroup = QButtonGroup()
        self._stocksButtonGroup.addButton(shIndexRadioButton, 1); 
        self._stocksButtonGroup.addButton(szIndexRadioButton, 2)
        self._stocksButtonGroup.addButton(cybIndexRadioButton, 3)
        self._stocksButtonGroup.addButton(zxbIndexRadioButton, 4)
        self._stocksButtonGroup.addButton(stockRadioButton, 5)

        # 布林周期
        bBands1PeriodLabel = QLabel('布林1周期')
        self._bBands1PeriodLineEdit = QLineEdit('10')
        bBands2PeriodLabel = QLabel('布林2周期')
        self._bBands2PeriodLineEdit = QLineEdit('20')

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
        grid.addWidget(stockRadioButton, 4, 0)
        grid.addWidget(self._stockLineEdit, 4, 1)

        grid.addWidget(bBands1PeriodLabel, 5, 0)
        grid.addWidget(self._bBands1PeriodLineEdit, 5, 1)
        grid.addWidget(bBands2PeriodLabel, 6, 0)
        grid.addWidget(self._bBands2PeriodLineEdit, 6, 1)

        grid.addWidget(okPushButton, 7, 1)
        grid.addWidget(cancelPushButton, 7, 0)
 
 
        self.setLayout(grid)

    def _radioButtonClicked(self, button):
        if button.text() == '股票代码':
            self._stockLineEdit.setEnabled(True)
        else:
            self._stockLineEdit.setEnabled(False)

    def _getStockCode(self):
        checkedButton = self._stocksButtonGroup.checkedButton()
        text = checkedButton.text()

        if text == '股票代码':
            return DyStockCommon.getDyStockCode(self._stockLineEdit.text())

        return DyStockCommon.getIndexByName(text)

    def _ok(self):
        self._data['startDate'] = self._startDateLineEdit.text()
        self._data['endDate'] = self._endDateLineEdit.text()
        self._data['code'] = self._getStockCode()
        self._data['bBands1Period'] = int(self._bBands1PeriodLineEdit.text())
        self._data['bBands2Period'] = int(self._bBands2PeriodLineEdit.text())

        self.accept()

    def _cancel(self):
        self.reject()
