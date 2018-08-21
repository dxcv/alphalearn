#!/usr/bin/env python
# -*- coding: utf-8 -*-
import pandas as pd
import numpy as np
import scipy as sp
from utils.tool import auto_sample
from dataProvider.trading_calendar import *


def continue_win(pct_series):
    """
    输入收益序列，返回最大连续盈利，亏损次数
    :return:
    """
    win_count = []
    lose_count = []
    win_num = 0
    lose_num = 0
    for i in pct_series.index:
        if pct_series.loc[i] > 0:
            lose_num = 0
            win_num += 1
            win_count.append(win_num)
        elif pct_series.loc[i] < 0:
            win_num = 0
            lose_num += 1
            lose_count.append(lose_num)
        else:
            win_num = 0
            lose_num = 0
            win_count.append(win_num)
            lose_count.append(lose_num)
    return np.max(win_count), np.max(lose_count)


def stutzer_index(pct_series):
    """
    stutzer_指数
    :return:
    """
    theta = np.arange(-15, 0, 0.01)
    risk_free = (1 + 0.03) ** (1.0 / 260) - 1
    temp_ip = [-np.log(sum(np.exp(theta[i] * (pct_series[:] - risk_free))) / len(pct_series)) for i in
               range(len(theta))]
    Stutzer = np.sign(np.mean(pct_series[:] - risk_free)) * np.sqrt(2 * abs(max(temp_ip)))
    return Stutzer


def days_from_highest_to_lowest(nav_series):
    """
    最大回撤持续期
    :param nav_series:
    :return:
    """
    maximum_list = []
    for i in range(1, len(nav_series)):
        maximum = np.array(nav_series)[i] - np.array(nav_series)[:i].max()
        maximum_list.append(maximum)
    return int(np.argmin(maximum_list) + 1) - int(np.argmax(np.array(nav_series)[:np.argmin(maximum_list) + 1]))


def days_recover_from_lowest_to_pre_max(nav_series):
    """
    最大净值恢复期
    :param nav_series:
    :return:
    """
    net_rec = []
    for i in range(1, len(nav_series)):
        if np.array(nav_series)[i] - np.array(nav_series)[:i].max() < 0:
            net_rec.append(i - np.argmax(np.array(nav_series)[:i]))
    return int(np.max(net_rec)) if len(net_rec) > 0 else None


def hurst(pct_series):
    """
    Hurst指数
    :param pct_series:
    :return:
    """

    """Returns the Hurst Exponent of the time series vector ts"""

    # create the range of lag values
    i = np.array(pct_series).size // 2
    lags = range(2, i)
    if len(lags) < 1:
        return None
    # Calculate the array of the variances of the lagged differences
    tau = [np.sqrt(np.std(np.subtract(np.array(pct_series)[lag:], np.array(pct_series)[:-lag]))) for lag in lags]
    # use a linear fit to estimate the Hurst Exponent
    poly = np.polyfit(np.log(lags), np.log(tau), 1)
    # Return the Hurst Exponent from the polyfit output
    return poly[0].item() * 2.0


def jensen_index(pct_series, bench_series, times):
    """
    詹森指数
    :param pct_series
    :param bench_pct_series:
    :param nav_type:
    :return:
    """
    if bench_series is None:
        return None
    bench_pct = bench_series.pct_change().dropna()
    #   选出交集
    inner_index = pct_series.index & bench_series.index
    if len(inner_index) == 0:
        return None
    bench_pct = bench_pct[inner_index]
    pct_series = pct_series[inner_index]
    frr = (0.04 + 1) * (np.size(bench_pct) / times) - 1
    beta = np.divide(np.cov(pct_series, bench_pct.loc[pct_series.index]),
                     np.cov(bench_pct, bench_pct))[0, 1]
    nav = (pct_series + 1).cumprod()
    return (nav[-1] - 1 - frr) * (1 - beta)


def month_win_rate(nav, bench_series):
    #   月度绝对，相对胜率，压力测试
    nav = auto_sample(nav, nav_type='M')
    bench_series = auto_sample(bench_series, nav_type='M')
    if len(nav) < 2:
        return None, None, None, None
    pct = nav.pct_change().dropna()
    bench_pct = bench_series.pct_change().dropna()
    Relative = pct - bench_pct
    #   绝对胜率，相对胜率
    month_max_drawdown = np.mean([nav.values[i:].min() / nav.values[i] - 1 for i in range(len(nav.values))])
    abs_rate = len(pct[pct > 0]) / len(pct)
    Relative_rate = len(Relative[Relative > 0]) / len(Relative)
    #   压力测试
    pressure_pct = bench_pct[bench_pct < -0.05]
    if len(pressure_pct) > 3:
        pressure_rate = len([i for i in pressure_pct.index if Relative.loc[i] > 0]) / len(pressure_pct)
    else:
        pressure_rate = None
    return abs_rate, Relative_rate, pressure_rate, month_max_drawdown


def this_year_annualized_profit(nav_series):
    """
    今年以来收益
    :param nav_series:
    :return:
    """
    this_year = datetime.datetime.now().strftime("%Y") + '0101'
    year_series = nav_series.loc[this_year:]
    if year_series.empty:
        return None
    else:
        return float(year_series.values[-1] / year_series.values[0] - 1)


def nav_performance(data, bench_series=None, nav_type=None, month=False):
    """
    输入基金代码，返回净值绩效
    :param assetCode:
    :return:
    """
    try:
        # 基于每日数据计算
        nav = data.dropna().copy()
        res = pd.Series()
        pct = nav.pct_change().dropna()
        if nav_type is None:
            tradingday_list = get_trading_day_range(str(nav.index[0]), str(nav.index[-1]))
            nav_type = ['D' if len(nav) / len(tradingday_list) >= 0.8 else 'W'][0]
        if nav_type == 'W':
            times = 52
        elif nav_type == 'D':
            times = 250
        #   近一月三月半年一年收益
        if nav_type == 'D':
            period_map = {'one_week': 5, 'one_month': 20, 'three_month': 60, 'six_month': 120,
                          'one_year': 250, 'two_year': 500, 'three_year': 750, 'five_year': 1250}
        elif nav_type == 'W':
            period_map = {'one_week': 1, 'one_month': 4, 'three_month': 12, 'six_month': 24,
                          'one_year': 50, 'two_year': 100, 'three_year': 150, 'five_year': 250}
        #   3月收益，6月收益，一年收益
        for key, day in period_map.items():
            res[key] = [float(nav.values[-1] / nav.values[-day] - 1) if len(nav) > day else None][0]
        res['accumulative_nav'] = nav.values[-1]
        res['ytd'] = this_year_annualized_profit(nav)
        res['annualized_return'] = (nav.values[-1] / nav.values[0]) ** (times / (len(nav.values) - 1)) - 1
        res['volatility'] = np.std(pct) * np.sqrt(times)
        res['down_volatility'] = np.std(pct[pct < 0])
        res['max_drawdown'] = min([nav.values[i:].min() / nav.values[i] - 1 for i in range(len(nav.values))])
        res['VaR95'] = pct.quantile(0.025)
        res['CvaR95'] = pct[pct < pct.quantile(0.025)].mean()
        res['kurtosis'] = sp.stats.kurtosis(pct)
        res['skew'] = sp.stats.skew(pct)
        res['sharpe'] = res['annualized_return'] / res['volatility']
        res['calmar'] = -1 * res['annualized_return'] / res['max_drawdown']
        res['sortino'] = res['annualized_return'] / np.sqrt(
            sum(pct[pct < 0].values ** 2) * times / (len(nav.values) - 1))
        res['stutzer'] = stutzer_index(pct)
        res['win_weeks'] = len(pct[pct > 0])
        res['loss_weeks'] = len(pct[pct < 0])
        res['win_rate'] = float(len(pct[pct > 0])) / len(nav.values)
        res['win_weeks_avg'] = pct[pct > 0].mean()
        res['loss_weeks_avg'] = pct[pct < 0].mean()
        res['win_lose_rate'] = pct[pct > 0].mean() / abs(pct[pct < 0].mean())
        res['max_week_win'] = max(pct)
        res['max_week_loss'] = min(pct)
        res['max_continuous_win'], res['max_continuous_loss'] = continue_win(pct)
        res['max_to_min'] = days_from_highest_to_lowest(nav)
        res['min_to_max'] = days_recover_from_lowest_to_pre_max(nav)
        res['jensen_index'] = jensen_index(pct, bench_series, times)
        if month:
            res['month_abs_win_rate'], res['month_rel_win_rate'], res['pressure_test'], res[
                'month_max_drawdown_mean'] = month_win_rate(nav, bench_series)
    except:
        print('xxx')
    return res


if __name__ == '__main__':
    nav_performance()
