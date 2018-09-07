# encoding: UTF-8

"""
这里的Demo是一个kdj策略实现
"""

from __future__ import division

from vnpy.trader.vtConstant import EMPTY_STRING, EMPTY_FLOAT
from vnpy.trader.app.ctaStrategy.ctaTemplate import (CtaTemplate,
                                                     BarGenerator,
                                                     ArrayManager)
from talib import MA_Type


########################################################################
class KDJStrategy(CtaTemplate):
    """KDJ策略Demo"""
    className = 'KDJStrategy'
    author = u'BillyZhang'

    # 策略参数
    fastk_period = 9
    slowk_period = 3
    slowk_matype = MA_Type.EMA
    slowd_period = 3
    slowd_matype = MA_Type.EMA
    kdlimit = 20
    jlimit = 10
    initDays = 10
    fixedSize = 1
    barmins = 15

    # 策略变量
    k = 0
    d = 0
    j = 0

    # 参数列表，保存了参数的名称
    paramList = ['name',
                 'className',
                 'author',
                 'vtSymbol',
                 'fastk_period',
                 'slowk_period',
                 'slowk_matype',
                 'slowd_period',
                 'slowd_matype',
                 'fixedSize'
                 'barmins'
                 ]

    # 变量列表，保存了变量的名称
    varList = ['inited',
               'pos',
               'k',
               'd',
               'j']

    # 同步列表，保存了需要保存到数据库的变量名称
    syncList = ['pos']

    # ----------------------------------------------------------------------
    def __init__(self, ctaEngine, setting):
        """Constructor"""
        super(KDJStrategy, self).__init__(ctaEngine, setting)

        self.bg = BarGenerator(self.onBar, self.barmins, self.onXminBar)
        self.am = ArrayManager()

        # 注意策略类中的可变对象属性（通常是list和dict等），在策略初始化时需要重新创建，
        # 否则会出现多个策略实例之间数据共享的情况，有可能导致潜在的策略逻辑错误风险，
        # 策略类中的这些可变对象属性可以选择不写，全都放在__init__下面，写主要是为了阅读
        # 策略时方便（更多是个编程习惯的选择）

    # ----------------------------------------------------------------------
    def onInit(self):
        """初始化策略（必须由用户继承实现）"""
        self.writeCtaLog(u'KDJ策略初始化')

        initData = self.loadBar(self.initDays)
        for bar in initData:
            self.onBar(bar)

        self.putEvent()

    # ----------------------------------------------------------------------
    def onStart(self):
        """启动策略（必须由用户继承实现）"""
        self.writeCtaLog(u'KDJ策略启动')
        self.putEvent()

    # ----------------------------------------------------------------------
    def onStop(self):
        """停止策略（必须由用户继承实现）"""
        self.writeCtaLog(u'KDJ策略停止')
        self.putEvent()

    # ----------------------------------------------------------------------
    def onTick(self, tick):
        """收到行情TICK推送（必须由用户继承实现）"""
        self.bg.updateTick(tick)

    # ----------------------------------------------------------------------
    def onBar(self, bar):
        """收到Bar推送（必须由用户继承实现）"""
        self.bg.updateBar(bar)

    # ----------------------------------------------------------------------
    def onXminBar(self, bar):
        """收到Bar推送（必须由用户继承实现）"""
        am = self.am
        am.updateBar(bar)
        if not am.inited:
            return

        # 计算kdj数值
        slowk, slowd, slowj = am.kdj(self.fastk_period, self.slowk_period, self.slowk_matype,
                                     self.slowd_period, self.slowd_matype, array=True)

        self.k = slowk[-1]
        self.d = slowd[-1]
        self.j = slowj[-1]
        self.jdif = slowj[-1] - slowj[-2]

        tradeindictor = 0
        if self.k > (100 - self.kdlimit) or self.d > (100 - self.kdlimit):
            tradeindictor = -1
        if self.k < self.kdlimit or self.d < self.kdlimit:
            tradeindictor = 1

        # 当前无仓位，发送开仓委托
        if self.pos == 0:
            self.intraTradeHigh = bar.high
            self.intraTradeLow = bar.low

            # 如果k值大于d值均线，开多单；反之，如果如果k值小于d值时候开空单
            if self.k > self.d and tradeindictor == 1:
                self.buy(bar.close, self.fixedSize, False)

            elif self.k < self.d and tradeindictor == -1:
                self.short(bar.close, self.fixedSize, False)

        # 持有多头仓位; 如果j小于d，或者j最近两个k线，j值下跌超过jlimi平仓, :
        elif self.pos > 0:
            if self.j < self.d or self.jdif < -1 *self.jlimit:
                self.sell(bar.close * 1.03, abs(self.pos))

        # 持有空头仓位;如果j大于d,或j快速上扬 平仓;
        elif self.pos < 0:
            if self.j > self.d or self.jdif > self.jlimit:
                self.cover(bar.close * 0.97, abs(self.pos))

        # 同步数据到数据库
        self.saveSyncData()

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