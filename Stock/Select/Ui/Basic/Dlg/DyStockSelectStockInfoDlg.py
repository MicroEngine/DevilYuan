from PyQt5.QtWidgets import QDialog, QGridLayout, QPushButton, QApplication, QMessageBox

from DyCommon.Ui.DyTreeWidget import *


class DyStockSelectStockInfoDlg(QDialog):
    """ 个股资料选择对话框
    """
    fields = \
        [
            ['公司资料',
                ['所属行业'],
                ['主营业务'],
                ['涉及概念']
            ],
            ['股本',
                ['实际流通股(亿)'],
                ['实际流通市值(亿元)'],
                ['机构占比流通(%)'],
            ]
        ]

    def __init__(self, data, parent=None):
        super().__init__(parent)

        self._data = data

        self._initUi()

    def _initUi(self):
        self.setWindowTitle('个股资料(F10)')
 
        # 控件
        cancelPushButton = QPushButton('Cancel')
        okPushButton = QPushButton('OK')
        cancelPushButton.clicked.connect(self._cancel)
        okPushButton.clicked.connect(self._ok)

        self._stockInfoWidget = DyTreeWidget(self.fields)

        # 布局
        grid = QGridLayout()
        grid.setSpacing(10)
 
        grid.addWidget(self._stockInfoWidget, 0, 0, 20, 10)
 
        grid.addWidget(okPushButton, 0, 10)
        grid.addWidget(cancelPushButton, 1, 10)
 
        self.setLayout(grid)
        self.resize(QApplication.desktop().size().width()//3, QApplication.desktop().size().height()//2)

    def _ok(self):
        indicators = self._stockInfoWidget.getCheckedTexts()

        if not indicators:
           QMessageBox.warning(self, '错误', '没有选择指标!')
           return

        self._data['indicators'] = indicators

        self.accept()

    def _cancel(self):
        self.reject()
