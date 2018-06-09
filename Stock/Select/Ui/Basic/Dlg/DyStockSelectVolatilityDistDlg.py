from PyQt5.QtWidgets import QApplication, QDialog, QGridLayout, QLabel, QLineEdit, QPushButton, QRadioButton, QButtonGroup


class DyStockSelectVolatilityDistDlg(QDialog):
    """
        !!!暂时这个类没有用
    """

    def __init__(self, name, baseDate, data, parent=None):
        """
            @name: 股票名称
        """
        super().__init__(parent)

        self._data = data

        self._initUi(name, baseDate)

    def _initUi(self, name, baseDate):
        self.setWindowTitle('波动分布[{0}]'.format(name))
 
        # 控件
        forwardNTDaysLabel = QLabel('基准日期[{0}]向前N日(不包含基准日期)'.format(baseDate))
        self._forwardNTDaysLineEdit = QLineEdit('30')

        # 自身波动和绝对波动
        # 个股绝对波动 = 个股自身波动 + 大盘波动
        selfVolatilityRadioButton = QRadioButton('自身波动'); selfVolatilityRadioButton.setChecked(True)
        selfVolatilityRadioButton.setToolTip('个股绝对波动 = 个股自身波动 + 大盘波动')

        absoluteVolatilityRadioButton = QRadioButton('绝对波动')
        absoluteVolatilityRadioButton.setToolTip('个股绝对波动 = 个股自身波动 + 大盘波动')

        # 添加到QButtonGroup
        self._volatilityButtonGroup = QButtonGroup()
        self._volatilityButtonGroup.addButton(selfVolatilityRadioButton, 1); 
        self._volatilityButtonGroup.addButton(absoluteVolatilityRadioButton, 2)

        cancelPushButton = QPushButton('Cancel')
        okPushButton = QPushButton('OK')
        cancelPushButton.clicked.connect(self._cancel)
        okPushButton.clicked.connect(self._ok)

        # 布局
        grid = QGridLayout()
        grid.setSpacing(10)
 
        grid.addWidget(forwardNTDaysLabel, 0, 0)
        grid.addWidget(self._forwardNTDaysLineEdit, 0, 1)

        grid.addWidget(selfVolatilityRadioButton, 1, 0)
        grid.addWidget(absoluteVolatilityRadioButton, 1, 1)

        grid.addWidget(okPushButton, 2, 1)
        grid.addWidget(cancelPushButton, 2, 0)
 
        self.setLayout(grid)

        self.setMinimumWidth(QApplication.desktop().size().width()//5)

    def _getVolatility(self):
        checkedButton = self._volatilityButtonGroup.checkedButton()
        text = checkedButton.text()

        return True if text == '自身波动' else False

    def _ok(self):
        self._data['forwardNTDays'] = int(self._forwardNTDaysLineEdit.text())
        self._data['selfVolatility'] = self._getVolatility()

        self.accept()

    def _cancel(self):
        self.reject()
