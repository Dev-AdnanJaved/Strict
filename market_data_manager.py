"""
Market Data Manager
Fetches and processes market data from Binance with indicators
"""
from typing import Dict, List
from binance_client import BinanceClient
from indicators import (
    calculate_adx_full_series,
    get_ema_all_timeframes,
    get_rsi_full_series,
    get_full_volume_series
)
from models import IndicatorData
import logging

logger = logging.getLogger(__name__)


class MarketDataManager:
    """
    Manages market data fetching and indicator calculation
    Integrates Binance client with indicator calculations
    """
    
    def __init__(
        self,
        binance_client: BinanceClient,
        ema_periods: List[int] = None,
        rsi_period: int = 14,
        adx_di_period: int = 14,
        adx_period: int = 14
    ):
        """
        Initialize market data manager
        
        Args:
            binance_client: BinanceClient instance
            ema_periods: List of EMA periods to calculate
            rsi_period: RSI period
            adx_di_period: ADX DI period
            adx_period: ADX smoothing period
        """
        self.client = binance_client
        self.ema_periods = ema_periods or [9, 25, 50, 99, 200]
        self.rsi_period = rsi_period
        self.adx_di_period = adx_di_period
        self.adx_period = adx_period
    
    def fetch_and_calculate_indicators(
        self,
        symbol: str,
        intervals: List[str],
        limit: int = 500
    ) -> Dict[str, IndicatorData]:
        """
        Fetch klines and calculate all indicators for a symbol
        
        Args:
            symbol: Trading pair (e.g., 'BTCUSDT')
            intervals: List of timeframes ['5m', '15m', '1h', etc.]
            limit: Number of candles to fetch
        
        Returns:
            dict: {interval: IndicatorData}
        """
        logger.info(f"Fetching data for {symbol}...")
        
        # Fetch raw klines
        klines_dict = self.client.fetch_klines_multiple(symbol, intervals, limit)
        
        # Check if we got data
        if not klines_dict or all(df.empty for df in klines_dict.values()):
            logger.warning(f"No data fetched for {symbol}")
            return {}
        
        # Calculate indicators
        logger.debug(f"Calculating indicators for {symbol}...")
        
        # EMA
        ema_data = get_ema_all_timeframes(klines_dict, self.ema_periods)
        
        # RSI
        rsi_data = get_rsi_full_series(klines_dict, self.rsi_period)
        
        # ADX
        adx_data = calculate_adx_full_series(
            klines_dict,
            self.adx_di_period,
            self.adx_period
        )
        
        # Volume
        volume_data = get_full_volume_series(klines_dict, use_quote=False)
        
        # Build IndicatorData objects
        result = {}
        
        for interval in intervals:
            if interval not in klines_dict or klines_dict[interval].empty:
                continue
            
            df = klines_dict[interval]
            
            # Create IndicatorData
            ind_data = IndicatorData(timeframe=interval)
            
            # Price data
            ind_data.close = df['close'].astype(float).tolist()
            ind_data.high = df['high'].astype(float).tolist()
            ind_data.low = df['low'].astype(float).tolist()
            ind_data.open = df['open'].astype(float).tolist()
            
            # Volume
            ind_data.volume = volume_data.get(interval, [])
            
            # EMAs
            if interval in ema_data:
                ind_data.ema9 = ema_data[interval].get('ema_9', [])
                ind_data.ema25 = ema_data[interval].get('ema_25', [])
                ind_data.ema50 = ema_data[interval].get('ema_50', [])
                ind_data.ema99 = ema_data[interval].get('ema_99', [])
                ind_data.ema200 = ema_data[interval].get('ema_200', [])
            
            # RSI
            ind_data.rsi = rsi_data.get(interval, [])
            
            # ADX
            ind_data.adx = adx_data.get(interval, [])
            
            result[interval] = ind_data
            
            logger.debug(
                f"  {interval}: {len(ind_data.close)} candles, "
                f"EMA50: {len(ind_data.ema50)}, "
                f"RSI: {len(ind_data.rsi)}, "
                f"ADX: {len(ind_data.adx)}"
            )
        
        logger.info(f"Indicators calculated for {symbol} ({len(result)} timeframes)")
        return result
    
    def fetch_multiple_symbols(
        self,
        symbols: List[str],
        intervals: List[str],
        limit: int = 500
    ) -> Dict[str, Dict[str, IndicatorData]]:
        """
        Fetch data and calculate indicators for multiple symbols
        
        Args:
            symbols: List of trading pairs
            intervals: List of timeframes
            limit: Number of candles per symbol
        
        Returns:
            dict: {symbol: {interval: IndicatorData}}
        """
        all_data = {}
        
        for symbol in symbols:
            try:
                symbol_data = self.fetch_and_calculate_indicators(
                    symbol, intervals, limit
                )
                
                if symbol_data:
                    all_data[symbol] = symbol_data
                else:
                    logger.warning(f"No data for {symbol}")
                    
            except Exception as e:
                logger.error(f"Error fetching {symbol}: {e}")
                continue
        
        logger.info(
            f"Fetched data for {len(all_data)}/{len(symbols)} symbols"
        )
        return all_data
    
    def get_indicator_summary(self, symbol: str, interval: str) -> dict:
        """
        Get a summary of current indicators for a symbol-interval
        
        Args:
            symbol: Trading pair
            interval: Timeframe
        
        Returns:
            dict: Summary of latest indicator values
        """
        data = self.fetch_and_calculate_indicators(symbol, [interval])
        
        if not data or interval not in data:
            return {}
        
        ind = data[interval]
        
        summary = {
            'symbol': symbol,
            'interval': interval,
            'price': ind.close[-1] if ind.close else None,
            'ema50': ind.ema50[-1] if ind.ema50 else None,
            'ema200': ind.ema200[-1] if ind.ema200 else None,
            'rsi': ind.rsi[-1] if ind.rsi else None,
            'adx': ind.adx[-1] if ind.adx else None,
            'volume': ind.volume[-1] if ind.volume else None,
            'candles': len(ind.close)
        }
        
        return summary
    
    def validate_data_quality(
        self,
        data: Dict[str, IndicatorData],
        min_candles: int = 200
    ) -> Dict[str, bool]:
        """
        Validate data quality for each timeframe
        
        Args:
            data: {interval: IndicatorData}
            min_candles: Minimum required candles
        
        Returns:
            dict: {interval: is_valid}
        """
        validation = {}
        
        for interval, ind_data in data.items():
            is_valid = (
                len(ind_data.close) >= min_candles and
                len(ind_data.ema50) >= min_candles and
                len(ind_data.ema200) >= min_candles and
                len(ind_data.rsi) >= min_candles and
                len(ind_data.adx) >= min_candles and
                len(ind_data.volume) >= min_candles
            )
            
            validation[interval] = is_valid
            
            if not is_valid:
                logger.warning(
                    f"{interval}: Insufficient data "
                    f"(close: {len(ind_data.close)}, "
                    f"ema50: {len(ind_data.ema50)}, "
                    f"rsi: {len(ind_data.rsi)}, "
                    f"adx: {len(ind_data.adx)})"
                )
        
        return validation
