from PyQt5.QtWidgets import QDialog, QGridLayout, QLabel, QTextEdit, QPushButton, QApplication, QCheckBox

from DyCommon.Ui.DyTableWidget import *


class DyStockSelectRefactoryParamsDlg(QDialog):

    def __init__(self, data, header, params, parent=None):
        super().__init__(parent)

        self._data = data

        self._initUi(header, params)

    def _initUi(self, header, params):
        self.setWindowTitle('重构参数')
 
        # 控件
        self._table = DyTableWidget(parent=None, readOnly=False, index=False, floatCut=True, autoScroll=False)
        self._table.setColNames(header)
        self._table.fastAppendRows(params)

        self._newWindowCheckBox = QCheckBox('新窗口')
        self._newWindowCheckBox.setChecked(True)

        cancelPushButton = QPushButton('Cancel')
        okPushButton = QPushButton('OK')
        cancelPushButton.clicked.connect(self._cancel)
        okPushButton.clicked.connect(self._ok)

        # 布局
        grid = QGridLayout()
        grid.setSpacing(10)
 
        grid.addWidget(self._newWindowCheckBox, 0, 0)
        grid.addWidget(self._table, 1, 0, 1, 2)
 
        grid.addWidget(okPushButton, 2, 1)
        grid.addWidget(cancelPushButton, 2, 0)
 
 
        self.setLayout(grid)
        self.resize(QApplication.desktop().size().width()//3, QApplication.desktop().size().height()//4*3)

    def _ok(self):
        params = self._table.getAll()
        params = {x[0]: x[1] for x in params}

        self._data['params'] = params
        self._data['newWindow'] = self._newWindowCheckBox.isChecked()

        self.accept()

    def _cancel(self):
        self.reject()
