# 写一个实盘策略
1. 在Stock\Trade\Strategy\Cta下添加一个策略文件  
![image](https://github.com/moyuanz/DevilYuan/blob/master/docs/trade/strategyPath.png)
2. 为了使策略能够被UI显示，需要在Stock\Trade\Ui\Basic\DyStockTradeStrategyWidget.py下添加如下代码  
![image](https://github.com/moyuanz/DevilYuan/blob/master/docs/trade/strategyUi.png)

# 策略回测
在主窗口打开策略回测窗口，勾选对应的策略即可回测。回测采用的类事件方式，跟实盘保持一致，这样导致回测比较慢。  
![image](https://github.com/moyuanz/DevilYuan/blob/master/docs/backtesting/resultDetails.png)

# 策略实盘
在主窗口打开实盘窗口。   
![image](https://github.com/moyuanz/DevilYuan/blob/master/docs/trade/trade.png)


# 策略文件解析
