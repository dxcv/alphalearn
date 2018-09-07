# encoding: UTF-8

"""
这里的Demo是一个最简单的双均线策略实现
"""

from __future__ import division

from vnpy.trader.vtConstant import EMPTY_STRING, EMPTY_FLOAT
from vnpy.trader.app.ctaStrategy.ctaTemplate import (CtaTemplate,
                                                     BarGenerator,
                                                     ArrayManager)
import tushare as ts
import talib as ta
import numpy as np
import datetime


########################################################################
class DoubleMaStrategy(CtaTemplate):
    """双指数均线策略Demo"""
    className = 'DoubleMaStrategy'
    author = u'用Python的交易员'

    # 策略参数
    fastWindow = 2  # 快速均线参数
    slowWindow = 5  # 慢速均线参数
    initDays = 1  # 初始化数据所用的天数

    exitTime0 = datetime.time(hour=14, minute=55)
    exitTime1 = datetime.time(hour=15, minute=0)
    atr_cond = 0  # atr条件
    open_count = 0  # 开仓次数限制
    open_time = 0  # 开仓时间
    open_price = EMPTY_FLOAT  # 开仓价格
    open_num = 1  # 开仓手数

    # 策略变量
    fastMa0 = EMPTY_FLOAT  # 当前最新的快速EMA
    fastMa1 = EMPTY_FLOAT  # 上一根的快速EMA

    slowMa0 = EMPTY_FLOAT
    slowMa1 = EMPTY_FLOAT

    # 参数列表，保存了参数的名称
    paramList = ['name',
                 'className',
                 'author',
                 'vtSymbol',
                 'fastWindow',
                 'slowWindow']

    # 变量列表，保存了变量的名称
    varList = ['inited',
               'trading',
               'pos',
               'fastMa0',
               'fastMa1',
               'slowMa0',
               'exitTime0',
               'exitTime1',
               'atr_cond'
               ]

    # 同步列表，保存了需要保存到数据库的变量名称
    syncList = ['pos']

    # ----------------------------------------------------------------------
    def __init__(self, ctaEngine, setting):
        """Constructor"""
        super(DoubleMaStrategy, self).__init__(ctaEngine, setting)

        # self.bg = BarGenerator(self.onBar)
        self.bg = BarGenerator(self.onBar, 5, self.onFiveBar)  # 创建K线合成器对象
        self.am = ArrayManager(10)

        # 注意策略类中的可变对象属性（通常是list和dict等），在策略初始化时需要重新创建，
        # 否则会出现多个策略实例之间数据共享的情况，有可能导致潜在的策略逻辑错误风险，
        # 策略类中的这些可变对象属性可以选择不写，全都放在__init__下面，写主要是为了阅读
        # 策略时方便（更多是个编程习惯的选择）

    # ----------------------------------------------------------------------
    def onInit(self):
        """初始化策略（必须由用户继承实现）"""
        self.writeCtaLog(u'双EMA演示策略初始化')

        initData = self.loadBar(self.initDays)
        for bar in initData:
            self.onBar(bar)

        self.putEvent()

    # ----------------------------------------------------------------------
    def onStart(self):
        """启动策略（必须由用户继承实现）"""
        self.writeCtaLog(u'双EMA演示策略启动')
        self.putEvent()

    # ----------------------------------------------------------------------
    def onStop(self):
        """停止策略（必须由用户继承实现）"""
        self.writeCtaLog(u'双EMA演示策略停止')
        self.putEvent()

    # ----------------------------------------------------------------------
    def onTick(self, tick):
        """收到行情TICK推送（必须由用户继承实现）"""
        self.bg.updateTick(tick)
        #   判断波动率是否符合条件,每天9点运行一次
        self.atr_cond = 0
        if self.atr_cond == 0 and tick.datetime.time() > datetime.time(hour=21, minute=0):
            self.atr_cond = self.atr_ma()

    # ----------------------------------------------------------------------
    def onBar(self, bar):
        """收到Bar推送（必须由用户继承实现）"""
        self.bg.updateBar(bar)

    # ----------------------------------------------------------------------
    def onFiveBar(self, bar):
        """收到Bar推送（必须由用户继承实现）"""
        am = self.am
        am.updateBar(bar)
        if not am.inited:
            return

        #   收盘平仓
        if self.exitTime0 < bar.datetime.time() < self.exitTime1:
            if self.pos > 0:
                self.sell(bar.close * 0.99, abs(self.pos))
            elif self.pos < 0:
                self.cover(bar.close * 1.01, abs(self.pos))
            return

        fastMa = am.sma(self.fastWindow, array=True)
        slowMa = am.sma(self.slowWindow, array=True)
        c0 = min(am.close[-3:]) < min(fastMa[-3], slowMa[-3])
        c1 = max(am.close[-3:]) > max(fastMa[-1], slowMa[-1])
        c2 = bar.close > max(am.close[-10:])
        c3 = min(am.close[-3:]) < min(fastMa[-1], slowMa[-1])
        c4 = max(am.close[-3:]) > max(fastMa[-3], slowMa[-3])
        c5 = bar.close < min(am.close[-10:])
        buy1 = c0 and c1 and c2
        sell1 = c3 and c4 and c5
        #   开仓
        if buy1:
            if self.pos == 0:
                self.buy(bar.close, 1)
                self.open_price = bar.close
                self.open_time = bar.datetime
        elif sell1:
            if self.pos == 0:
                self.short(bar.close, 1)
                self.open_price = bar.close
                self.open_time = bar.datetime

        #   平仓
        if self.pos != 0 and self.open_price != 0:
            #   平多
            p0 = bar.close < self.open_price - am.atr(10) * 1
            p1 = bar.close < self.open_price - am.atr(10) * 2
            #   平空
            p2 = bar.close > self.open_price + am.atr(10) * 1
            p3 = bar.close > self.open_price + am.atr(10) * 2
            t0 = bar.datetime - self.open_time
            if self.pos > 0:
                if (p0 and t0.minute < 60) or (p1 and t0.minute >= 60):
                    self.sell(bar.close, abs(self.pos))
            elif self.pos < 0:
                if (p2 and t0.minute < 60) or (p3 and t0.minute >= 60):
                    self.cover(bar.close, abs(self.pos))
        # 发出状态更新事件
        self.putEvent()

    # ----------------------------------------------------------------------
    def onOrder(self, order):
        """收到委托变化推送（必须由用户继承实现）"""
        # 对于无需做细粒度委托控制的策略，可以忽略onOrder
        pass

    # ----------------------------------------------------------------------
    def onTrade(self, trade):
        """收到成交推送（必须由用户继承实现）"""
        # 对于无需做细粒度委托控制的策略，可以忽略onOrder
        pass

    # ----------------------------------------------------------------------
    def onStopOrder(self, so):
        """停止单推送"""
        pass

    def atr_ma(self):
        now = datetime.datetime.now()
        start_date = now - datetime.timedelta(30)
        end_date = [now if 20 < now.hour <= 23 else now - datetime.timedelta(1)][0]
        tem = ts.bar('rb1901', conn=ts.get_apis(), start_date=start_date, end_date=end_date, asset='X').sort_index()
        C = np.array(tem['close'])
        H = np.array(tem['high'])
        L = np.array(tem['low'])
        TR = ta.ATR(H, L, C, 1) / C[-2]
        ATR10 = ta.ATR(H, L, C, 10) / C[-2]
        res = [1 if TR[-1] < ATR10[-1] and ATR10[-1] > 0.02 else -1][0]
        return res


if __name__ == "__main__":
    pass
