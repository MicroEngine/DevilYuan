DY_STOCK_DATA_HIST_TICKS_HAND_NBR = 2

class DyStockDataEventHandType:
    
    stockHistTicksHandNbr = DY_STOCK_DATA_HIST_TICKS_HAND_NBR
    ticksEngine = DY_STOCK_DATA_HIST_TICKS_HAND_NBR
    daysEngine = DY_STOCK_DATA_HIST_TICKS_HAND_NBR + 1
    strategyDataPrepare = DY_STOCK_DATA_HIST_TICKS_HAND_NBR + 2
    other = DY_STOCK_DATA_HIST_TICKS_HAND_NBR + 3

    nbr = DY_STOCK_DATA_HIST_TICKS_HAND_NBR + 4


class DyStockHistTicksReqData:
    def __init__(self, code, date):
        self.code = code
        self.date = date

class DyStockHistTicksAckData:
    noData = 'noData'

    def __init__(self, code, date, data):
        self.code = code
        self.date = date
        self.data = data

"""
                ["股本指标",
                    ["流通A股", 'float_a_shares'],
                    ["A股合计", 'share_totala']
                ],
                
                ["行情指标",
                    ["开盘价", 'open'],
                    ["收盘价", 'close'],
                    ["最高价", 'high'],
                    ["最低价", 'low'],
                    ["成交量", 'volume'],
                    ["成交额", 'amt'],
                    ["换手率", 'turn'],
                    ["净流入资金", 'mf_amt'],
                    ["净流入量", 'mf_vol']
                ],
"""
class DyStockDataCommon:
    # Wind的volume是成交量，单位是股数。数据库里的成交量也是股数。
    dayIndicators = ['open', 'high', 'low', 'close', 'volume', 'amt', 'turn', 'adjfactor']
    adjFactor = 'adjfactor'

    logDetailsEnabled = False

    defaultHistTicksDataSource = '智能' # '新浪', '腾讯' , '网易', '智能'
