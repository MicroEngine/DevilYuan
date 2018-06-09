from PyQt5.QtWidgets import QDialog, QLabel, QVBoxLayout
from PyQt5.QtGui import QFont


class DyInfoDlg(QDialog):
    """显示信息"""

    def __init__(self, title, info, parent=None):
        super().__init__(parent)

        self.setWindowTitle(title)

        self._initUi(info)

    def _initUi(self, info):
        text = info

        label = QLabel()
        label.setText(text)
        label.setMinimumWidth(500)

        label.setFont(QFont('Courier New', 12))

        vbox = QVBoxLayout()
        vbox.addWidget(label)

        self.setLayout(vbox)