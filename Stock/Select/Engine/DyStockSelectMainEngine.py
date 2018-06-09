from EventEngine.DyEventEngine import *
from ..DyStockSelectCommon import *
from DyCommon.DyCommon import *
from .DyStockSelectSelectEngine import *
from .Regression.DyStockSelectRegressionEngine import *
from ...Data.Viewer.DyStockDataViewer import *
from .DyStockSelectViewerEngine import *


class DyStockSelectMainEngine(object):

    def __init__(self):
        self._eventEngine = DyEventEngine(DyStockSelectEventHandType.nbr, False)
        self._info = DyInfo(self._eventEngine)

        self._selectEngine = DyStockSelectSelectEngine(self._eventEngine, self._info)
        self._regressionEngine = DyStockSelectRegressionEngine(self._eventEngine, self._info)
        self._viewerEngine = DyStockSelectViewerEngine(self._eventEngine, self._info)

        self._initDataViewer()

        self._eventEngine.start()

    @property
    def eventEngine(self):
        return self._eventEngine

    @property
    def info(self):
        return self._info

    def exit(self):
        pass

    def _initDataViewer(self):
        errorInfo = DyErrorInfo(self._eventEngine)
        dataEngine = DyStockDataEngine(self._eventEngine, errorInfo, False)
        self._dataViewer = DyStockDataViewer(dataEngine, errorInfo)

    @property
    def dataViewer(self):
        return self._dataViewer
