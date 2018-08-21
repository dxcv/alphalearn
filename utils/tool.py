from utils.trading_calendar import *
import pandas as pd


def auto_sample(nav_series, nav_type=None):
    """
    重采样nav. 按照交易日
    :param nav_series: 有序的series
    :param index_name
    :param nav_type W周净值 D日净值
    :return:
    """
    if nav_type is None:
        tradingday_list = get_trading_day_range(nav_series.index[0], nav_series.index[-1])
        nav_type = ['D' if len(nav_series) / len(tradingday_list) >= 0.8 else 'W'][0]
    #   获取交易日区间
    day_list = get_trading_day_range(nav_series.index[0], nav_series.index[-1])
    if nav_type == 'D':
        nav_series = nav_series.loc[day_list].interpolate()
    elif nav_type == 'W':
        week_list = get_trading_week_day_range(nav_series.index[0], nav_series.index[-1])
        nav_series = nav_series.loc[day_list].interpolate()
        nav_series = nav_series.loc[week_list].interpolate()
    elif nav_type == 'M':
        month_list = get_trading_month_day_range(nav_series.index[0], nav_series.index[-1])
        nav_series = nav_series.loc[day_list].interpolate()
        nav_series = nav_series.loc[month_list].interpolate()
    nav_series = nav_series.dropna()
    return nav_series


def winsorize_series(se):
    q = se.quantile([0.025, 0.975])
    if isinstance(q, pd.Series) and len(q) == 2:
        se[se < q.iloc[0]] = q.iloc[0]
        se[se > q.iloc[1]] = q.iloc[1]
    return se


def standardize_series(se):
    se_std = se.std()
    se_mean = se.mean()
    return (se - se_mean) / se_std
