"""
Trading Bot Configuration
All parameters, thresholds, and settings in one place
"""
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Binance API Configuration
BINANCE_CONFIG = {
    'api_key': os.getenv('BINANCE_API_KEY', ''),
    'api_secret': os.getenv('BINANCE_API_SECRET', ''),
    'base_url': 'https://fapi.binance.com',
    'candles_limit': 500,
}

# Symbol Selection Configuration
SYMBOL_CONFIG = {
    # Options: 'top_volume', 'all', or 'custom'
    'mode': 'top_volume',
    
    # If mode='top_volume', how many top coins by volume
    # Set to None to fetch all coins
    'top_n_coins': 400,
    
    # If mode='custom', specify symbols here
    'custom_symbols': ['BTCUSDT', 'ETHUSDT', 'BNBUSDT'],
    
    # Minimum 24h quote volume filter (in USDT)
    # Set to 0 to disable
    'min_volume_filter': 0,  # 10M USDT   #10_000_000
}

# Timeframes to monitor
TIMEFRAMES = ['15m']

# Indicator Periods
INDICATOR_PERIODS = {
    'ema': [50,200], #[9, 25, 50, 99, 200]
    'rsi': 14,
    'adx': 14,
}

# Signal Detection Parameters
SIGNAL_CONFIG = {
    # EMA Cross Detection
    'cross_emas': [50, 200],  # EMA50/EMA200 cross
    'cross_lookback': 5,  # Check last 5 candles for cross (prevents missing crosses if loop is slow)
    
    # Window after cross (in candles) - NO MINIMUM WAIT TIME
    'evaluation_window': 96,  # Monitor for 96 candles (24 hours on 15m)
    
    # Trend Strength (COMPULSORY - both timeframes must pass)
    'adx_threshold_15m': 25,  # ADX must be > 25 on 15m
    'adx_threshold_1h': 22,   # ADX must be > 22 on 1h
    
    # Momentum Bias (COMPULSORY - both timeframes must pass)
    'rsi_threshold_15m': 50,  # RSI must be > 50 on 15m
    'rsi_threshold_1h': 50,   # RSI must be > 50 on 1h
    
    # Structure Hold (OPTIONAL - not required for signal)
    'structure_lookback': 5,
    'structure_min_holds': 2,
    
    # Reclaim Pattern (OPTIONAL - not required for signal)
    'reclaim_lookback': 4,
    
    # EMA Expansion (COMPULSORY)
    'expansion_threshold': 0.002,  # 0.2% - MUST be expanding (stronger requirement)
    
    # Slope Filter (COMPULSORY - EMA200 MUST be rising)
    # Checks if current EMA200 > EMA200 at cross (simple comparison)
    
    # Volume (COMPULSORY - checked AT CROSS TIME)
    'volume_cross_window': 2,     # Check ±2 candles around cross (5 total)
    'volume_baseline_period': 50,  # Baseline 50 candles before cross (more stable)
    'volume_min_ratio': 2.0,      # MUST be 3x baseline at cross
}

# COMPULSORY CRITERIA (signal only sent if ALL pass):
# 1. Current price ABOVE EMA200 (basic sanity check)
# 2. ADX > 25 on 15m AND > 22 on 1h
# 3. RSI > 50 on 15m AND > 50 on 1h
# 4. EMAs expanding (>0.2%)
# 5. EMA200 slope rising (current > at cross)
# 6. Volume at cross >= 3x baseline (50-candle baseline)
# 
# NOTE: Structure and Reclaim are calculated but NOT required
# NOTE: No minimum time wait - checks immediately after cross

# Telegram Configuration
TELEGRAM_CONFIG = {
    'bot_token': os.getenv('TELEGRAM_BOT_TOKEN', ''),
    'chat_id': os.getenv('TELEGRAM_CHAT_ID', ''),
    'enable_notifications': True,
}

# Alert Messages Templates
ALERT_TEMPLATES = {
    'confirmed': """
✅ CONFIRMED SIGNAL — {symbol} ({timeframe})

💰 Price: ${price:.2f} | EMA200: ${ema200:.2f}
🚀 EMA Expansion: {expansion:.2%}
📈 EMA200 Change: +{slope_change:.2%} since cross
💪 ADX 15m: {adx_15m:.1f} | 1h: {adx_1h:.1f}
📊 RSI 15m: {rsi_15m:.1f} | 1h: {rsi_1h:.1f}
📊 Volume at Cross: {volume_ratio:.1f}x

💎 ALL CRITERIA MET
""",
}

# Logging Configuration
LOGGING_CONFIG = {
    'level': 'INFO',
    'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    'file': 'trading_bot.log',
}
