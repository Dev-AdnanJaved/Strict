"""
Data Models for Trading Bot
Structured data containers for market data and indicators
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from datetime import datetime


@dataclass
class CandleData:
    """Single candle/bar data"""
    timestamp: int
    open: float
    high: float
    low: float
    close: float
    volume: float
    
    def __repr__(self):
        return f"Candle(t={self.timestamp}, c={self.close:.2f}, v={self.volume:.0f})"


@dataclass
class IndicatorData:
    """All indicators for a single timeframe"""
    timeframe: str
    candles: List[CandleData] = field(default_factory=list)
    
    # Price data (500 values)
    close: List[float] = field(default_factory=list)
    high: List[float] = field(default_factory=list)
    low: List[float] = field(default_factory=list)
    open: List[float] = field(default_factory=list)
    volume: List[float] = field(default_factory=list)
    
    # EMA values (500 values each)
    ema9: List[float] = field(default_factory=list)
    ema25: List[float] = field(default_factory=list)
    ema50: List[float] = field(default_factory=list)
    ema99: List[float] = field(default_factory=list)
    ema200: List[float] = field(default_factory=list)
    
    # RSI (500 values)
    rsi: List[float] = field(default_factory=list)
    
    # ADX (500 values)
    adx: List[float] = field(default_factory=list)
    
    def __len__(self):
        return len(self.close)
    
    def get_latest(self, indicator: str, lookback: int = 1) -> List[float]:
        """Get latest N values of an indicator"""
        data = getattr(self, indicator, [])
        if not data:
            return []
        return data[-lookback:] if lookback > 1 else [data[-1]]


@dataclass
class MarketData:
    """All market data for a symbol across timeframes"""
    symbol: str
    last_update: datetime = field(default_factory=datetime.now)
    timeframes: Dict[str, IndicatorData] = field(default_factory=dict)
    
    def add_timeframe(self, timeframe: str, data: IndicatorData):
        """Add or update timeframe data"""
        self.timeframes[timeframe] = data
        self.last_update = datetime.now()
    
    def get_timeframe(self, timeframe: str) -> Optional[IndicatorData]:
        """Get data for specific timeframe"""
        return self.timeframes.get(timeframe)
    
    def has_sufficient_data(self, timeframe: str, min_candles: int = 200) -> bool:
        """Check if timeframe has enough data"""
        tf_data = self.get_timeframe(timeframe)
        return tf_data and len(tf_data) >= min_candles


@dataclass
class CrossEvent:
    """Detected EMA cross event"""
    symbol: str
    timeframe: str
    cross_index: int  # Index where cross occurred
    cross_type: str  # 'bullish' or 'bearish'
    detection_time: datetime = field(default_factory=datetime.now)
    ema_fast: int = 50
    ema_slow: int = 200
    
    def candles_since_cross(self, current_index: int) -> int:
        """Calculate candles elapsed since cross"""
        return current_index - self.cross_index
    
    def is_within_window(self, current_index: int, window: int = 24) -> bool:
        """Check if still within evaluation window"""
        return self.candles_since_cross(current_index) <= window


@dataclass
class SignalFeatures:
    """Computed features for signal evaluation"""
    # Trend indicators (COMPULSORY - both timeframes)
    trend_ok: bool = False
    adx_value_15m: float = 0.0  # ADX on 15m timeframe
    adx_value_1h: float = 0.0   # ADX on 1h timeframe
    
    # Momentum (COMPULSORY - both timeframes)
    momentum_ok: bool = False
    rsi_value_15m: float = 0.0  # RSI on 15m timeframe
    rsi_value_1h: float = 0.0   # RSI on 1h timeframe
    
    # Structure
    structure_ok: bool = False
    hold_count: int = 0
    
    # Reclaim pattern
    reclaim: bool = False
    
    # EMA expansion
    expanding: bool = False
    expansion_spread: float = 0.0
    
    # Slope
    slope_rising: bool = False
    slope_ratio: float = 0.0
    
    # Volume
    volume_score: int = 0
    volume_ratio: float = 0.0
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for logging"""
        return {
            'trend_ok': self.trend_ok,
            'adx_15m': self.adx_value_15m,
            'adx_1h': self.adx_value_1h,
            'momentum_ok': self.momentum_ok,
            'rsi_15m': self.rsi_value_15m,
            'rsi_1h': self.rsi_value_1h,
            'structure_ok': self.structure_ok,
            'hold_count': self.hold_count,
            'reclaim': self.reclaim,
            'expanding': self.expanding,
            'expansion': self.expansion_spread,
            'slope_rising': self.slope_rising,
            'volume_score': self.volume_score,
            'volume_ratio': self.volume_ratio,
        }


@dataclass
class Signal:
    """Complete signal with score and features"""
    symbol: str
    timeframe: str
    signal_type: str  # 'confirmed' or 'weak'
    score: int
    max_score: int
    features: SignalFeatures
    cross_event: CrossEvent
    timestamp: datetime = field(default_factory=datetime.now)
    hours_since_cross: float = 0.0  # Hours since cross happened
    current_price: float = 0.0  # Current price at signal
    current_ema200: float = 0.0  # Current EMA200 at signal
    
    def score_percentage(self) -> float:
        """Get score as percentage"""
        return (self.score / self.max_score) * 100 if self.max_score > 0 else 0.0
    
    def is_early_alert(self, threshold: int) -> bool:
        """Check if meets early alert criteria"""
        return self.score >= threshold and self.signal_type == 'early'
    
    def is_confirmed_alert(self, threshold: int) -> bool:
        """Check if meets confirmed alert criteria"""
        return self.score >= threshold and self.signal_type == 'confirmed'
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for storage/logging"""
        return {
            'symbol': self.symbol,
            'timeframe': self.timeframe,
            'type': self.signal_type,
            'score': self.score,
            'max_score': self.max_score,
            'percentage': self.score_percentage(),
            'features': self.features.to_dict(),
            'timestamp': self.timestamp.isoformat(),
        }


@dataclass
class RegimeState:
    """Track regime state for a symbol-timeframe pair"""
    symbol: str
    timeframe: str
    active_cross: Optional[CrossEvent] = None
    last_check_index: int = 0
    sent_early_alert: bool = False
    sent_confirmed_alert: bool = False
    
    def reset(self):
        """Reset regime state"""
        self.active_cross = None
        self.sent_early_alert = False
        self.sent_confirmed_alert = False
    
    def set_cross(self, cross_event: CrossEvent):
        """Set new cross event"""
        self.active_cross = cross_event
        self.sent_early_alert = False
        self.sent_confirmed_alert = False
    
    def should_evaluate(self, current_index: int, window: int = 24) -> bool:
        """Check if should evaluate signal"""
        if not self.active_cross:
            return False
        return self.active_cross.is_within_window(current_index, window)
