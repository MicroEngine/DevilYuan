from datetime import *

from PyQt5.QtWidgets import QDialog, QGridLayout, QLabel, QLineEdit, QPushButton, QCheckBox


class DyStockDataHistTicksVerifyDlg(QDialog):

    def __init__(self, data, parent=None):
        super().__init__(parent)

        self._data = data

        self._initUi()

    def _initUi(self):
        self.setWindowTitle('历史分笔数据校验')
 
        # 控件
        startDateLable = QLabel('开始日期')
        self._startDateLineEdit = QLineEdit(datetime.now().strftime("%Y-%m-%d"))

        endDateLable = QLabel('结束日期')
        self._endDateLineEdit = QLineEdit(datetime.now().strftime("%Y-%m-%d"))

        self._addCheckBox = QCheckBox('校验缺失历史分笔数据')
        self._addCheckBox.setChecked(True)
        self._deleteCheckBox = QCheckBox('校验无效历史分笔数据')
        #self._deleteCheckBox.setChecked(True)

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

        grid.addWidget(self._addCheckBox, 2, 0)
        grid.addWidget(self._deleteCheckBox, 2, 1)

        grid.addWidget(okPushButton, 3, 1)
        grid.addWidget(cancelPushButton, 3, 0)
 
        self.setLayout(grid)

    def _ok(self):
        self._data['startDate'] = self._startDateLineEdit.text()
        self._data['endDate'] = self._endDateLineEdit.text()

        self._data['verifyMissing'] = self._addCheckBox.isChecked()
        self._data['verifyInvalid'] = self._deleteCheckBox.isChecked()

        self.accept()

    def _cancel(self):
        self.reject()
