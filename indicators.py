"""
Indicators Module
Exact implementation of ADX, EMA, RSI, and Volume indicators
"""
import pandas as pd
import numpy as np
import logging

logger = logging.getLogger(__name__)


def rma_tv(series, period):
    """TradingView-style RMA (Wilder's Moving Average)."""
    series = series.copy()
    result = pd.Series(np.nan, index=series.index)
    result.iloc[period-1] = series.iloc[:period].mean()  # first value = mean
    for i in range(period, len(series)):
        result.iloc[i] = (result.iloc[i-1]*(period-1) + series.iloc[i])/period
    return result


def calculate_adx_multi_intervals(data_dict, di_period=14, adx_period=14):
    """
    Calculate ADX for multiple intervals - Exact TradingView logic
    
    Args:
        data_dict: {interval: DataFrame} with high, low, close columns
        di_period: DI period (default: 14)
        adx_period: ADX smoothing period (default: 14)
    
    Returns:
        dict: {interval: adx_value}
    """
    adx_result = {}
    
    for interval, df in data_dict.items():
        df = df.copy()
        df["high"] = df["high"].astype(float)
        df["low"] = df["low"].astype(float)
        df["close"] = df["close"].astype(float)

        up = df["high"].diff()
        down = -df["low"].diff()

        plus_dm = up.where((up > down) & (up > 0), 0.0)
        minus_dm = down.where((down > up) & (down > 0), 0.0)

        tr = pd.concat([
            df["high"] - df["low"],
            (df["high"] - df["close"].shift(1)).abs(),
            (df["low"] - df["close"].shift(1)).abs()
        ], axis=1).max(axis=1)

        # Smooth using RMA (Wilder's MA)
        tr_rma = rma_tv(tr, di_period)
        plus_rma = rma_tv(plus_dm, di_period)
        minus_rma = rma_tv(minus_dm, di_period)

        # +DI and -DI
        plus_di = 100 * (plus_rma / tr_rma)
        minus_di = 100 * (minus_rma / tr_rma)

        # DX
        dx = (plus_di - minus_di).abs() / (plus_di + minus_di)
        dx.fillna(0, inplace=True)

        # ADX smoothing
        adx_series = rma_tv(dx, adx_period) * 100  # scale after smoothing

        # Drop initial NaNs (unstable values)
        adx_valid = adx_series.dropna()
        if len(adx_valid) == 0:
            adx_result[interval] = np.nan
        else:
            adx_result[interval] = round(adx_valid.iloc[-1], 2)

    return adx_result


def calculate_adx_full_series(data_dict, di_period=14, adx_period=14):
    """
    Calculate full ADX series (all 500 values) for multiple intervals
    
    Returns:
        dict: {interval: [adx_values]}
    """
    adx_result = {}
    
    for interval, df in data_dict.items():
        df = df.copy()
        df["high"] = df["high"].astype(float)
        df["low"] = df["low"].astype(float)
        df["close"] = df["close"].astype(float)

        up = df["high"].diff()
        down = -df["low"].diff()

        plus_dm = up.where((up > down) & (up > 0), 0.0)
        minus_dm = down.where((down > up) & (down > 0), 0.0)

        tr = pd.concat([
            df["high"] - df["low"],
            (df["high"] - df["close"].shift(1)).abs(),
            (df["low"] - df["close"].shift(1)).abs()
        ], axis=1).max(axis=1)

        # Smooth using RMA (Wilder's MA)
        tr_rma = rma_tv(tr, di_period)
        plus_rma = rma_tv(plus_dm, di_period)
        minus_rma = rma_tv(minus_dm, di_period)

        # +DI and -DI
        plus_di = 100 * (plus_rma / tr_rma)
        minus_di = 100 * (minus_rma / tr_rma)

        # DX
        dx = (plus_di - minus_di).abs() / (plus_di + minus_di)
        dx.fillna(0, inplace=True)

        # ADX smoothing
        adx_series = rma_tv(dx, adx_period) * 100  # scale after smoothing

        # Store full series
        adx_result[interval] = adx_series.fillna(0).tolist()

    return adx_result


def get_ema_all_timeframes(data_dict, ema_periods):
    """
    Returns full EMA series for all candles
    
    Structure:
    {
        "15m": {
            "ema_9":   [...500 values...],
            "ema_25":  [...],
            "ema_50":  [...],
            "ema_99":  [...],
            "ema_200": [...]
        },
        "1h": {...},
        ...
    }
    """
    ema_result = {}

    for tf, df in data_dict.items():
        # ensure float
        df["close"] = df["close"].astype(float)

        ema_result[tf] = {}

        # calculate EMAs
        for period in ema_periods:
            ema_series = df["close"].ewm(
                span=period,
                adjust=False
            ).mean()

            # store FULL list of values
            ema_result[tf][f"ema_{period}"] = ema_series.tolist()

    return ema_result


def get_latest_rsi(candle_data_dict, period=14):
    """
    Calculate latest RSI per interval exactly like Binance Futures.

    Returns:
    - dict {interval: latest RSI value (float)}
    """
    latest_rsi = {}

    for interval, df in candle_data_dict.items():
        if df.empty:
            latest_rsi[interval] = None
            continue

        close = df["close"].astype(float)
        delta = close.diff()

        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)

        # First average gain/loss: SMA of first 'period' candles
        avg_gain = gain[:period].mean()
        avg_loss = loss[:period].mean()

        # Recursive calculation for all candles after the first 'period'
        for i in range(period, len(gain)):
            avg_gain = (avg_gain * (period - 1) + gain.iloc[i]) / period
            avg_loss = (avg_loss * (period - 1) + loss.iloc[i]) / period

        # Calculate RSI
        rs = avg_gain / avg_loss if avg_loss != 0 else float('inf')
        rsi = 100 - (100 / (1 + rs))

        latest_rsi[interval] = rsi

    return latest_rsi


def get_rsi_full_series(candle_data_dict, period=14):
    """
    Calculate full RSI series (all 500 values) per interval
    
    Returns:
        dict: {interval: [rsi_values]}
    """
    rsi_result = {}

    for interval, df in candle_data_dict.items():
        if df.empty:
            rsi_result[interval] = []
            continue

        close = df["close"].astype(float)
        delta = close.diff()

        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)

        # Initialize with first period SMA
        avg_gain = gain[:period].mean()
        avg_loss = loss[:period].mean()

        # Create result array
        rsi_values = [np.nan] * period  # First 'period' values are NaN
        
        # Calculate RSI for each point
        for i in range(period, len(gain)):
            avg_gain = (avg_gain * (period - 1) + gain.iloc[i]) / period
            avg_loss = (avg_loss * (period - 1) + loss.iloc[i]) / period
            
            rs = avg_gain / avg_loss if avg_loss != 0 else float('inf')
            rsi = 100 - (100 / (1 + rs))
            rsi_values.append(rsi)

        rsi_result[interval] = rsi_values

    return rsi_result


def get_last_n_volume_with_pressure(candle_data_dict, last_n, use_quote=False):
    """
    Returns volume, buy, and sell volumes for the last N candles per interval.

    Parameters:
    - candle_data_dict : dict {interval: DataFrame} from fetch_klines_multiple
    - last_n : int, how many recent candles to return
    - use_quote : bool, True for quote volume ("qav"), False for base asset volume ("volume")

    Returns:
    - dict : {interval: {"volume": [], "buy": [], "sell": []}}
    """
    volumes = {}

    for interval, df in candle_data_dict.items():
        if df.empty:
            volumes[interval] = {"volume": [], "buy": [], "sell": []}
            continue

        # Choose volume column
        vol_col = "qav" if use_quote else "volume"

        # Get last N candles
        last_candles = df.tail(last_n)

        base_vol = last_candles[vol_col].astype(float).tolist()
        taker_buy = last_candles["taker_base_vol"].astype(float).tolist()
        taker_sell = [b - buy for b, buy in zip(base_vol, taker_buy)]

        volumes[interval] = {"volume": base_vol, "buy": taker_buy, "sell": taker_sell}

    return volumes


def get_full_volume_series(candle_data_dict, use_quote=False):
    """
    Returns full volume series (all 500 values) per interval
    
    Returns:
        dict: {interval: [volume_values]}
    """
    volumes = {}

    for interval, df in candle_data_dict.items():
        if df.empty:
            volumes[interval] = []
            continue

        # Choose volume column
        vol_col = "qav" if use_quote else "volume"

        # Get all volumes
        volumes[interval] = df[vol_col].astype(float).tolist()

    return volumes
