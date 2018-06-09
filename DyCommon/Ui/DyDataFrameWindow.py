from PyQt5.QtWidgets import QApplication

from .DyDataFrameTableWidget import *


class DyDataFrameWindow(DyDataFrameTableWidget):
    """ 显示DataFrame """

    def __init__(self, title, df, parent=None):
        super().__init__(df, parent)

        self._initUi(title)

    def _initUi(self, title):
        self.setWindowTitle(title)
        self.setWindowFlags(Qt.Window)
        self.resize(QApplication.desktop().size().width()//2, QApplication.desktop().size().height()//2)

        self.show()

        self.move((QApplication.desktop().size().width() - self.width())//2, (QApplication.desktop().size().height() - self.height())//2)
