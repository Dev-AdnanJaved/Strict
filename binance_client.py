"""
Binance Client Module
Handles all Binance Futures API interactions
"""
import requests
import hmac
import hashlib
import time
from typing import Dict, List, Optional
import pandas as pd
import logging

logger = logging.getLogger(__name__)


class BinanceClient:
    """
    Binance Futures API Client
    Handles authentication and data fetching
    """
    
    def __init__(self, api_key: str = None, api_secret: str = None):
        """
        Initialize Binance client
        
        Args:
            api_key: Binance API key (optional for public endpoints)
            api_secret: Binance API secret (optional for public endpoints)
        """
        self.api_key = api_key
        self.api_secret = api_secret
        self.base_url = "https://fapi.binance.com"
        self.session = requests.Session()
        
        if api_key:
            self.session.headers.update({
                'X-MBX-APIKEY': api_key
            })
    
    def _get_signature(self, params: dict) -> str:
        """Generate HMAC SHA256 signature"""
        query_string = '&'.join([f"{k}={v}" for k, v in params.items()])
        signature = hmac.new(
            self.api_secret.encode('utf-8'),
            query_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        return signature
    
    def _request(self, method: str, endpoint: str, params: dict = None, signed: bool = False):
        """Make API request"""
        url = f"{self.base_url}{endpoint}"
        params = params or {}
        
        if signed:
            params['timestamp'] = int(time.time() * 1000)
            params['signature'] = self._get_signature(params)
        
        try:
            response = self.session.request(method, url, params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Binance API error: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response: {e.response.text}")
            raise
    
    def get_exchange_info(self) -> dict:
        """
        Get exchange information (all trading pairs)
        
        Returns:
            dict: Exchange info
        """
        return self._request('GET', '/fapi/v1/exchangeInfo')
    
    def get_all_symbols(self) -> List[str]:
        """
        Get all USDT futures trading pairs
        
        Returns:
            List of symbol names (e.g., ['BTCUSDT', 'ETHUSDT', ...])
        """
        exchange_info = self.get_exchange_info()
        symbols = [
            s['symbol'] for s in exchange_info['symbols']
            if s['status'] == 'TRADING' and s['quoteAsset'] == 'USDT'
        ]
        logger.info(f"Found {len(symbols)} active USDT futures pairs")
        return symbols
    
    def get_top_volume_symbols(self, top_n: int = 20) -> List[str]:
        """
        Get top N symbols by 24h quote volume
        
        Args:
            top_n: Number of top symbols to return
            
        Returns:
            List of top symbols
        """
        ticker_24h = self._request('GET', '/fapi/v1/ticker/24hr')
        
        # Filter USDT pairs and sort by quote volume
        usdt_pairs = [
            t for t in ticker_24h
            if t['symbol'].endswith('USDT')
        ]
        
        sorted_pairs = sorted(
            usdt_pairs,
            key=lambda x: float(x['quoteVolume']),
            reverse=True
        )
        
        top_symbols = [p['symbol'] for p in sorted_pairs[:top_n]]
        
        logger.info(f"Top {top_n} volume symbols: {', '.join(top_symbols[:5])}...")
        return top_symbols
    
    def get_klines(
        self,
        symbol: str,
        interval: str,
        limit: int = 500
    ) -> pd.DataFrame:
        """
        Get kline/candlestick data for a symbol
        
        Args:
            symbol: Trading pair (e.g., 'BTCUSDT')
            interval: Timeframe ('1m', '5m', '15m', '1h', '4h', '1d')
            limit: Number of candles (max 1500, default 500)
        
        Returns:
            DataFrame with columns: open_time, open, high, low, close, volume, 
                                   close_time, qav, trades, taker_base_vol, taker_quote_vol
        """
        params = {
            'symbol': symbol,
            'interval': interval,
            'limit': limit
        }
        
        data = self._request('GET', '/fapi/v1/klines', params=params)
        
        # Convert to DataFrame
        df = pd.DataFrame(data, columns=[
            'open_time', 'open', 'high', 'low', 'close', 'volume',
            'close_time', 'qav', 'trades', 'taker_base_vol', 'taker_quote_vol', 'ignore'
        ])
        
        # Convert types
        df['open_time'] = pd.to_datetime(df['open_time'], unit='ms')
        df['close_time'] = pd.to_datetime(df['close_time'], unit='ms')
        
        numeric_cols = ['open', 'high', 'low', 'close', 'volume', 'qav', 
                       'taker_base_vol', 'taker_quote_vol']
        for col in numeric_cols:
            df[col] = df[col].astype(float)
        
        df['trades'] = df['trades'].astype(int)
        df = df.drop('ignore', axis=1)
        
        return df
    
    def fetch_klines_multiple(
        self,
        symbol: str,
        intervals: List[str],
        limit: int = 500
    ) -> Dict[str, pd.DataFrame]:
        """
        Fetch klines for multiple intervals
        
        Args:
            symbol: Trading pair
            intervals: List of intervals ['5m', '15m', '1h', etc.]
            limit: Number of candles per interval
        
        Returns:
            dict: {interval: DataFrame}
        """
        result = {}
        
        for interval in intervals:
            try:
                df = self.get_klines(symbol, interval, limit)
                result[interval] = df
                logger.debug(f"Fetched {len(df)} candles for {symbol} {interval}")
            except Exception as e:
                logger.error(f"Failed to fetch {symbol} {interval}: {e}")
                result[interval] = pd.DataFrame()
        
        return result
    
    def get_ticker_24h(self, symbol: str = None) -> dict:
        """
        Get 24h ticker price change statistics
        
        Args:
            symbol: Trading pair (if None, returns all)
        
        Returns:
            dict or list: Ticker data
        """
        params = {}
        if symbol:
            params['symbol'] = symbol
        
        return self._request('GET', '/fapi/v1/ticker/24hr', params=params)
    
    def get_current_price(self, symbol: str) -> float:
        """
        Get current price for a symbol
        
        Args:
            symbol: Trading pair
        
        Returns:
            float: Current price
        """
        params = {'symbol': symbol}
        data = self._request('GET', '/fapi/v1/ticker/price', params=params)
        return float(data['price'])
    
    def test_connectivity(self) -> bool:
        """
        Test API connectivity
        
        Returns:
            bool: True if connected
        """
        try:
            self._request('GET', '/fapi/v1/ping')
            logger.info("Binance API connection successful")
            return True
        except Exception as e:
            logger.error(f"Binance API connection failed: {e}")
            return False
    
    def get_server_time(self) -> int:
        """
        Get server time
        
        Returns:
            int: Server timestamp in milliseconds
        """
        data = self._request('GET', '/fapi/v1/time')
        return data['serverTime']
