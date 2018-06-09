# Check user package intelligently
from Stock.Common.DyStockCommon import DyStockCommon

try:
    from WindPy import *
except ImportError:
    print("DevilYuan-Warnning: Import WindPy error, switch default data source of stock history days to TuShare!")
    DyStockCommon.WindPyInstalled = False