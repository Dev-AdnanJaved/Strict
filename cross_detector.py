"""
Cross Detector Module
Detects EMA crossover events (bullish and bearish)
"""
from typing import Optional, List
from models import CrossEvent, IndicatorData
from config import SIGNAL_CONFIG
import logging

logger = logging.getLogger(__name__)


class CrossDetector:
    """Detects EMA crossover events"""
    
    def __init__(self, fast_ema: int = 50, slow_ema: int = 200):
        """
        Initialize cross detector
        
        Args:
            fast_ema: Fast EMA period (default: 50)
            slow_ema: Slow EMA period (default: 200)
        """
        self.fast_ema = fast_ema
        self.slow_ema = slow_ema
        
    def detect_cross(
        self, 
        symbol: str, 
        timeframe: str, 
        data: IndicatorData,
        lookback: int = 5
    ) -> Optional[CrossEvent]:
        """
        Detect EMA cross in the most recent candle(s)
        
        Args:
            symbol: Trading pair symbol
            timeframe: Timeframe string
            data: Indicator data
            lookback: How many candles back to check (default: 5 to catch missed crosses)
            
        Returns:
            CrossEvent if cross detected, None otherwise
        """
        # Get EMA data
        ema_fast = getattr(data, f'ema{self.fast_ema}', [])
        ema_slow = getattr(data, f'ema{self.slow_ema}', [])
        
        # Validate data
        if len(ema_fast) < lookback + 1 or len(ema_slow) < lookback + 1:
            logger.warning(f"Insufficient EMA data for {symbol} {timeframe}")
            return None
        
        # Check last N candles for cross (most recent first)
        # This catches crosses even if loop took longer than expected
        current_idx = len(ema_fast) - 1
        
        for i in range(lookback):
            check_idx = current_idx - i
            prev_idx = check_idx - 1
            
            fast_prev = ema_fast[prev_idx]
            fast_curr = ema_fast[check_idx]
            slow_prev = ema_slow[prev_idx]
            slow_curr = ema_slow[check_idx]
            
            # Detect bullish cross (fast crosses above slow)
            if fast_prev <= slow_prev and fast_curr > slow_curr:
                logger.info(f"Bullish cross detected: {symbol} {timeframe} at index {check_idx} ({i} candles back)")
                return CrossEvent(
                    symbol=symbol,
                    timeframe=timeframe,
                    cross_index=check_idx,
                    cross_type='bullish',
                    ema_fast=self.fast_ema,
                    ema_slow=self.slow_ema
                )
            
            # Detect bearish cross (fast crosses below slow)
            if fast_prev >= slow_prev and fast_curr < slow_curr:
                logger.info(f"Bearish cross detected: {symbol} {timeframe} at index {check_idx} ({i} candles back)")
                return CrossEvent(
                    symbol=symbol,
                    timeframe=timeframe,
                    cross_index=check_idx,
                    cross_type='bearish',
                    ema_fast=self.fast_ema,
                    ema_slow=self.slow_ema
                )
        
        return None
    
    def find_recent_crosses(
        self, 
        symbol: str, 
        timeframe: str, 
        data: IndicatorData,
        max_lookback: int = 50
    ) -> List[CrossEvent]:
        """
        Find all crosses within recent history
        
        Args:
            symbol: Trading pair symbol
            timeframe: Timeframe string
            data: Indicator data
            max_lookback: Maximum candles to look back
            
        Returns:
            List of CrossEvents found
        """
        ema_fast = getattr(data, f'ema{self.fast_ema}', [])
        ema_slow = getattr(data, f'ema{self.slow_ema}', [])
        
        if len(ema_fast) < 2 or len(ema_slow) < 2:
            return []
        
        crosses = []
        data_len = len(ema_fast)
        start_idx = max(1, data_len - max_lookback)
        
        for i in range(start_idx, data_len):
            fast_prev = ema_fast[i - 1]
            fast_curr = ema_fast[i]
            slow_prev = ema_slow[i - 1]
            slow_curr = ema_slow[i]
            
            # Bullish cross
            if fast_prev <= slow_prev and fast_curr > slow_curr:
                crosses.append(CrossEvent(
                    symbol=symbol,
                    timeframe=timeframe,
                    cross_index=i,
                    cross_type='bullish',
                    ema_fast=self.fast_ema,
                    ema_slow=self.slow_ema
                ))
            
            # Bearish cross
            elif fast_prev >= slow_prev and fast_curr < slow_curr:
                crosses.append(CrossEvent(
                    symbol=symbol,
                    timeframe=timeframe,
                    cross_index=i,
                    cross_type='bearish',
                    ema_fast=self.fast_ema,
                    ema_slow=self.slow_ema
                ))
        
        return crosses
    
    def get_cross_strength(
        self, 
        data: IndicatorData, 
        cross_event: CrossEvent
    ) -> float:
        """
        Calculate strength of cross based on separation
        
        Args:
            data: Indicator data
            cross_event: The cross event to analyze
            
        Returns:
            Strength value (0.0 to 1.0+)
        """
        ema_fast = getattr(data, f'ema{self.fast_ema}', [])
        ema_slow = getattr(data, f'ema{self.slow_ema}', [])
        
        if not ema_fast or not ema_slow:
            return 0.0
        
        # Current separation
        current_separation = abs(ema_fast[-1] - ema_slow[-1])
        separation_pct = current_separation / ema_slow[-1] if ema_slow[-1] != 0 else 0
        
        return separation_pct
    
    def is_valid_cross(
        self, 
        data: IndicatorData, 
        cross_event: CrossEvent,
        min_separation: float = 0.0001  # 0.01%
    ) -> bool:
        """
        Validate if cross is significant enough
        
        Args:
            data: Indicator data
            cross_event: Cross event to validate
            min_separation: Minimum separation percentage
            
        Returns:
            True if valid cross
        """
        strength = self.get_cross_strength(data, cross_event)
        return strength >= min_separation
