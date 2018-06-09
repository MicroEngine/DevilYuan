from datetime import *

from PyQt5.QtWidgets import QDialog, QGridLayout, QLabel, QLineEdit, QPushButton, QCheckBox

from ....Common.DyStockCommon import *


class DyStockSelectIndexMaStatsDlg(QDialog):

    def __init__(self, data, parent=None):
        super().__init__(parent)

        self._data = data

        self._initUi()

    def _initUi(self):
        self.setWindowTitle('指数均线统计')
 
        # 控件
        startDateLable = QLabel('开始日期')
        self._startDateLineEdit = QLineEdit(datetime.now().strftime("%Y-%m-%d"))

        endDateLable = QLabel('结束日期')
        self._endDateLineEdit = QLineEdit(datetime.now().strftime("%Y-%m-%d"))

        # 图示哪些指标
        showIndicatorLabel = QLabel('图示指标')

        # 收盘价和成交量
        self._maCheckBoxes = []
        self._vmaCheckBoxes = []
        for ma in [5, 10, 20, 30, 60]:
            self._maCheckBoxes.append(QCheckBox(str(ma) + '日均线'))
            self._maCheckBoxes[-1].setChecked(True)

            self._vmaCheckBoxes.append(QCheckBox(str(ma) + '日量均线'))

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

        grid.addWidget(showIndicatorLabel, 3, 0)

        for i, maCheckBox in enumerate(self._maCheckBoxes):
            grid.addWidget(maCheckBox, 4 + i, 0)

        for i, vmaCheckBox in enumerate(self._vmaCheckBoxes):
            grid.addWidget(vmaCheckBox, 4 + i, 1)

        grid.addWidget(okPushButton, 4 + i + 1, 1)
        grid.addWidget(cancelPushButton, 4 + i + 1, 0)
 
        self.setLayout(grid)

    def _ok(self):
        self._data['startDate'] = self._startDateLineEdit.text()
        self._data['endDate'] = self._endDateLineEdit.text()

        self._data['mas'] = []
        for maCheckBox in self._maCheckBoxes:
            if maCheckBox.isChecked():
                self._data['mas'].append(int(maCheckBox.text()[:-3]))

        self._data['vmas'] = []
        for vmaCheckBox in self._vmaCheckBoxes:
            if vmaCheckBox.isChecked():
                self._data['vmas'].append(int(vmaCheckBox.text()[:-4]))

        self.accept()

    def _cancel(self):
        self.reject()
