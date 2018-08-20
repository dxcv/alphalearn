#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2017/10/20 0020 11:32
# @Author  : yukuai
# @Site    : 
# @File    : trading_day.py
# @Software: PyCharm
import datetime
import tushare as ts


__ALL__ = [
    'is_trading_day',
    'get_pre_trading_day',
    'get_pre_trading_day_range',
    'get_next_trading_day_range',
    'get_trading_day_range',
    'get_next_trading_day',
    'get_lately_trading_day',
    'get_lately_week_trading_day',
    'get_trading_week_day_range',
]


def init_calendar():
    obj = init_calendar
    cache_name = 'trading_days'
    if not hasattr(obj, cache_name):
        ts.set_token('0503684c1ca87a31116049960065adbf985e0c052adb268a2b5397dd')
        pro = ts.pro_api()
        trading_days = pro.trade_cal(exchange_id='SSE', start_date='20070101', end_date='', is_open='1')['cal_date'].tolist()
        setattr(obj, cache_name, trading_days)
    return getattr(obj, cache_name)


def init_trading_week_day():
    obj = init_trading_week_day
    cache_name = 'trading_week_days'
    if not hasattr(obj, cache_name):
        trading_days = init_calendar()
        trading_week_days = []
        pre_index_week = None
        for str_date in sorted(trading_days, reverse=True):
            date = datetime.datetime.strptime(str_date, '%Y%m%d')
            _, index_week, week_day = date.isocalendar()
            if index_week != pre_index_week:
                trading_week_days.insert(0, str_date)
            pre_index_week = index_week
        if len(trading_week_days) > 0 and trading_week_days[-1] == trading_days[-1]:
            date = datetime.datetime.strptime(trading_week_days[-1], '%Y%m%d')
            # 如果最后一周不是周五, 就丢掉
            if date.isoweekday() != 5:
                trading_week_days = trading_week_days[:-1]
        setattr(obj, cache_name, trading_week_days)
    return getattr(obj, cache_name)


def init_trading_month_day():
    obj = init_trading_month_day
    cache_name = 'trading_month_days'
    if not hasattr(obj, cache_name):
        trading_days = init_calendar()
        trading_month_days = []
        pre_index_month = None
        for str_date in sorted(trading_days, reverse=True):
            date = datetime.datetime.strptime(str_date, '%Y%m%d')
            index_month = date.month
            if index_month != pre_index_month:
                trading_month_days.insert(0, str_date)
            pre_index_month = index_month
        if len(trading_month_days) > 0 and trading_month_days[-1] == trading_days[-1]:
            date = datetime.datetime.strptime(trading_month_days[-1], '%Y%m%d')
            # 如果最后一周不是周五, 就丢掉
            if date.isoweekday() != 5:
                trading_month_days = trading_month_days[:-1]
        setattr(obj, cache_name, trading_month_days)
    return getattr(obj, cache_name)


def is_trading_day(date=None):
    """
    返回指定日期是否是交易日, date为None 则返回当天是否是交易日
    :param date: 
    :return: 
    """
    trading_days = init_calendar()
    date = date or datetime.datetime.now().strftime("%Y%m%d")
    return date in trading_days


def get_pre_trading_day(date=None, n=1):
    """
    获取上n个交易日. 如果当天不是交易日,则返回最近一个交易日的上n个交易日.
    :param date: 
    :param n: 
    :return: 
    """
    trading_days = init_calendar()
    date = get_lately_trading_day(date)
    return trading_days[trading_days.index(date) - n]


def get_pre_trading_day_range(date=None, n=1):
    """
    获取到date到上n个交易日之间的所有交易日,  将返回n个元素的list
    :param date: 
    :param n: 
    :return: 
    """
    trading_days = init_calendar()
    date = get_lately_trading_day(date)
    index = trading_days.index(date)
    return trading_days[index - n: index]


def get_next_trading_day_range(date=None, n=1):
    """
    获取到date到下n个交易日之间的所有交易日, 将返回n个元素的list. 不包含date.
    :param date: 是None将替换为当天, 如果不是交易日替换为上个交易日.
    :param n: 
    :return: 
    """
    trading_days = init_calendar()
    date = get_lately_trading_day(date)
    index = trading_days.index(date)
    return trading_days[index + 1: index + 1 + n]


def get_trading_day_range(begin_date=None, end_date=None):
    """
    返回以begin_date开始,end_date结束的交易日列表. 包含begin_date和end_date
    全部为None 返回全部交易日的列表
    如果参数不会是交易日, 将替换为上个交易日
    :param begin_date: 是None将替换为当天, 如果不是交易日替换为上个交易日.
    :param end_date: 是None将替换为当天, 如果不是交易日替换为上个交易日.
    :return: 
    """
    trading_days = init_calendar()
    if begin_date is None and end_date is None:
        return trading_days
    begin_date = get_lately_trading_day(begin_date)
    end_date = get_lately_trading_day(end_date)
    b = trading_days.index(begin_date)
    e = trading_days.index(end_date)
    return trading_days[b:e + 1]


def get_next_trading_day(date=None, n=1):
    """
    获取下n个交易日. 如果当天不是交易日,则返回最近一个交易日的下n个交易日.
    :param date: 是None将替换为当天, 如果不是交易日替换为上个交易日.
    :param n: 
    :return: 
    """
    trading_days = init_calendar()
    date = get_lately_trading_day(date)
    return trading_days[trading_days.index(date) + n]


def get_lately_trading_day(date=None):
    """
    获取指定日期的最近一个交易日,如果当天不是交易日则返回上个交易日,如果当天是交易日则返回当天
    :param date: 
    :return: 
    """

    if date is None:
        date_time = datetime.datetime.now()
    else:
        date_time = datetime.datetime.strptime(date, '%Y%m%d')
    trading_days = init_calendar()
    for i in range(len(trading_days)):
        _date = (date_time - datetime.timedelta(days=i)).strftime("%Y%m%d")
        if _date in trading_days:
            return _date
    else:
        raise ValueError(
            'date error or out of range. date: %s. range: %s~%s' % (date, trading_days[0], trading_days[-1]))


def get_lately_week_trading_day(date=None):
    """
    获取指定日期的最近一个周交易日.如果当天不是周交易日则返回上个周交易日,如果当天是周交易日则返回当天
    :param date: 
    :return: 
    """

    if date is None:
        date_time = datetime.datetime.now()
    else:
        date_time = datetime.datetime.strptime(date, '%Y%m%d')
    trading_week_days = init_trading_week_day()
    for i in range(len(trading_week_days)):
        _date = (date_time - datetime.timedelta(days=i)).strftime("%Y%m%d")
        if _date in trading_week_days:
            return _date
    else:
        raise ValueError(
            'date error or out of range. date: %s. range: %s~%s' % (date, trading_week_days[0], trading_week_days[-1]))


def get_trading_week_day_range(begin_date=None, end_date=None):
    """
    返回交易日范围.起止都为None,返回全部
    :param begin_date: 
    :param end_date: 
    :return: 
    """
    trading_week_days = init_trading_week_day()
    if begin_date is None and end_date is None:
        return trading_week_days
    begin_date = get_lately_week_trading_day(begin_date)
    end_date = get_lately_week_trading_day(end_date)
    b = trading_week_days.index(begin_date)
    e = trading_week_days.index(end_date)
    return trading_week_days[b:e + 1]


def get_lately_month_trading_day(date=None):
    """
    获取指定日期的最近一个月交易日
    :param date: 
    :return: 
    """

    if date is None:
        date_time = datetime.datetime.now()
    else:
        date_time = datetime.datetime.strptime(date, '%Y%m%d')
    trading_month_days = init_trading_month_day()
    for i in range(len(trading_month_days)):
        _date = (date_time - datetime.timedelta(days=i)).strftime("%Y%m%d")
        if _date in trading_month_days:
            return _date
    else:
        raise ValueError(
            'date error or out of range. date: %s. range: %s~%s' % (
            date, trading_month_days[0], trading_month_days[-1]))


def get_trading_month_day_range(begin_date=None, end_date=None):
    """
    返回交易日范围.起止都为None,返回全部
    :param begin_date: 
    :param end_date: 
    :return: 
    """
    trading_month_days = init_trading_month_day()
    if begin_date is None and end_date is None:
        return trading_month_days
    begin_date = get_lately_month_trading_day(begin_date)
    end_date = get_lately_month_trading_day(end_date)
    b = trading_month_days.index(begin_date)
    e = trading_month_days.index(end_date)
    return trading_month_days[b:e + 1]
