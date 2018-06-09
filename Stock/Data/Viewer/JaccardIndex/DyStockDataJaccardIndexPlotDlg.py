from PyQt5.QtWidgets import QDialog, QGridLayout, QPushButton, QApplication, QMessageBox

from DyCommon.Ui.DyTreeWidget import *


class DyStockDataJaccardIndexPlotDlg(QDialog):
    """ 选择哪些杰卡德指数可视化
    """
    def __init__(self, data, columns, parent=None):
        super().__init__(parent)

        self._data = data
        self._columns = columns

        self._initUi()

    def _initUi(self):
        self.setWindowTitle('选择哪些杰卡德指数可视化')
 
        # 控件
        cancelPushButton = QPushButton('Cancel')
        okPushButton = QPushButton('OK')
        cancelPushButton.clicked.connect(self._cancel)
        okPushButton.clicked.connect(self._ok)

        self._jaccardIndexWidget = DyTreeWidget([[x] for x in self._columns])

        # 布局
        grid = QGridLayout()
        grid.setSpacing(10)
 
        grid.addWidget(self._jaccardIndexWidget, 0, 0, 20, 2)
 
        grid.addWidget(okPushButton, 20, 1)
        grid.addWidget(cancelPushButton, 20, 0)
 
        self.setLayout(grid)
        self.resize(QApplication.desktop().size().width()//6, QApplication.desktop().size().height()//2)

    def _ok(self):
        names = self._jaccardIndexWidget.getCheckedTexts()

        if not names:
           QMessageBox.warning(self, '错误', '没有选择杰卡德指数!')
           return

        self._data['data'] = names

        self.accept()

    def _cancel(self):
        self.reject()
