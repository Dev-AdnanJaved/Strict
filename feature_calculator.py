"""
Feature Calculator Module
Computes all features for signal evaluation
"""
from typing import List
from models import SignalFeatures, IndicatorData, CrossEvent
from config import SIGNAL_CONFIG
import logging

logger = logging.getLogger(__name__)


class FeatureCalculator:
    """Calculates all signal features"""
    
    def __init__(self, config: dict = None):
        """
        Initialize feature calculator
        
        Args:
            config: Configuration dict (defaults to SIGNAL_CONFIG)
        """
        self.config = config or SIGNAL_CONFIG
    
    def calculate_all_features(
        self, 
        data_15m: IndicatorData,
        data_1h: IndicatorData,
        cross_event: CrossEvent
    ) -> SignalFeatures:
        """
        Calculate all features for signal evaluation
        Now requires BOTH 15m and 1h data for multi-timeframe confirmation
        
        Args:
            data_15m: Indicator data for 15m timeframe
            data_1h: Indicator data for 1h timeframe
            cross_event: Active cross event
            
        Returns:
            SignalFeatures object with all computed features
        """
        features = SignalFeatures()
        
        # Calculate each feature (ALL are now COMPULSORY)
        features.trend_ok, features.adx_value_15m, features.adx_value_1h = self._check_trend_strength(data_15m, data_1h)
        features.momentum_ok, features.rsi_value_15m, features.rsi_value_1h = self._check_momentum_bias(data_15m, data_1h)
        features.structure_ok, features.hold_count = self._check_structure_hold(data_15m)
        features.reclaim = self._check_reclaim_pattern(data_15m)
        features.expanding, features.expansion_spread = self._check_ema_expansion(data_15m)
        features.slope_rising, features.slope_ratio = self._check_slope_filter(
            data_15m, cross_event
        )
        # Volume checked AT CROSS TIME (not current)
        features.volume_score, features.volume_ratio = self._calculate_volume_score(data_15m, cross_event)
        
        return features
    
    def check_minimum_time_since_cross(
        self,
        cross_event: CrossEvent,
        current_index: int,
        timeframe: str = '15m'
    ) -> tuple[bool, float]:
        """
        Check if cross happened at least N hours ago (COMPULSORY)
        
        Args:
            cross_event: The cross event
            current_index: Current candle index
            timeframe: Timeframe string (to calculate hours)
            
        Returns:
            (meets_requirement: bool, hours_since_cross: float)
        """
        min_hours = self.config['min_hours_since_cross']
        candles_since_cross = current_index - cross_event.cross_index
        
        # Convert candles to hours based on timeframe
        timeframe_minutes = {
            '1m': 1, '3m': 3, '5m': 5, '15m': 15, '30m': 30,
            '1h': 60, '2h': 120, '4h': 240, '6h': 360, '12h': 720, '1d': 1440
        }
        
        minutes_per_candle = timeframe_minutes.get(timeframe, 15)  # Default to 15m
        hours_since_cross = (candles_since_cross * minutes_per_candle) / 60.0
        
        meets_requirement = hours_since_cross >= min_hours
        
        logger.debug(
            f"Time since cross: {hours_since_cross:.1f} hours "
            f"({candles_since_cross} candles on {timeframe}) "
            f"- Minimum: {min_hours} hours {'✓' if meets_requirement else '✗'}"
        )
        
        return meets_requirement, hours_since_cross
    
    def _check_trend_strength(self, data_15m: IndicatorData, data_1h: IndicatorData) -> tuple[bool, float, float]:
        """
        Check trend strength using ADX on BOTH timeframes (COMPULSORY)
        
        Returns:
            (trend_ok: bool, adx_15m: float, adx_1h: float)
            trend_ok is True ONLY if BOTH timeframes pass their thresholds
        """
        # Check 15m ADX
        if not data_15m.adx:
            return False, 0.0, 0.0
        adx_15m = data_15m.adx[-1]
        adx_threshold_15m = self.config['adx_threshold_15m']
        passed_15m = adx_15m > adx_threshold_15m
        
        # Check 1h ADX
        if not data_1h.adx:
            logger.debug("No 1h ADX data available")
            return False, adx_15m, 0.0
        adx_1h = data_1h.adx[-1]
        adx_threshold_1h = self.config['adx_threshold_1h']
        passed_1h = adx_1h > adx_threshold_1h
        
        # BOTH must pass
        trend_ok = passed_15m and passed_1h
        
        logger.debug(
            f"ADX Check: 15m={adx_15m:.2f} (threshold: {adx_threshold_15m}) {'✓' if passed_15m else '✗'}, "
            f"1h={adx_1h:.2f} (threshold: {adx_threshold_1h}) {'✓' if passed_1h else '✗'} "
            f"-> {'PASS' if trend_ok else 'FAIL'}"
        )
        return trend_ok, adx_15m, adx_1h
    
    def _check_momentum_bias(self, data_15m: IndicatorData, data_1h: IndicatorData) -> tuple[bool, float, float]:
        """
        Check momentum bias using RSI on BOTH timeframes (COMPULSORY)
        
        Returns:
            (momentum_ok: bool, rsi_15m: float, rsi_1h: float)
            momentum_ok is True ONLY if BOTH timeframes pass their thresholds
        """
        # Check 15m RSI
        if not data_15m.rsi:
            return False, 0.0, 0.0
        rsi_15m = data_15m.rsi[-1]
        rsi_threshold_15m = self.config['rsi_threshold_15m']
        passed_15m = rsi_15m > rsi_threshold_15m
        
        # Check 1h RSI
        if not data_1h.rsi:
            logger.debug("No 1h RSI data available")
            return False, rsi_15m, 0.0
        rsi_1h = data_1h.rsi[-1]
        rsi_threshold_1h = self.config['rsi_threshold_1h']
        passed_1h = rsi_1h > rsi_threshold_1h
        
        # BOTH must pass
        momentum_ok = passed_15m and passed_1h
        
        logger.debug(
            f"RSI Check: 15m={rsi_15m:.2f} (threshold: {rsi_threshold_15m}) {'✓' if passed_15m else '✗'}, "
            f"1h={rsi_1h:.2f} (threshold: {rsi_threshold_1h}) {'✓' if passed_1h else '✗'} "
            f"-> {'PASS' if momentum_ok else 'FAIL'}"
        )
        return momentum_ok, rsi_15m, rsi_1h
    
    def _check_structure_hold(self, data: IndicatorData) -> tuple[bool, int]:
        """
        Check structure hold pattern
        Price holding above EMA200 for majority of recent candles
        
        Returns:
            (structure_ok: bool, hold_count: int)
        """
        lookback = self.config['structure_lookback']
        min_holds = self.config['structure_min_holds']
        
        if len(data.close) < lookback or len(data.ema200) < lookback:
            return False, 0
        
        # Count how many recent closes are above EMA200
        hold_count = sum(
            1 for i in range(-lookback, 0)
            if data.close[i] > data.ema200[i]
        )
        
        structure_ok = hold_count >= min_holds
        
        logger.debug(
            f"Structure hold: {hold_count}/{lookback} candles "
            f"(min: {min_holds}) - {'✓' if structure_ok else '✗'}"
        )
        return structure_ok, hold_count
    
    def _check_reclaim_pattern(self, data: IndicatorData) -> bool:
        """
        Check reclaim pattern:
        - Price dipped below EMA200 recently
        - But current price is back above EMA200
        
        Returns:
            reclaim: bool
        """
        lookback = self.config['reclaim_lookback']
        
        if len(data.close) < lookback or len(data.ema200) < lookback:
            return False
        
        # Check if minimum of last 3 closes (excluding current) was below EMA200
        recent_lows = data.close[-(lookback):-1]  # Last 3 candles before current
        recent_ema200 = data.ema200[-(lookback):-1]
        
        min_close = min(recent_lows) if recent_lows else float('inf')
        min_ema200 = min(recent_ema200) if recent_ema200 else float('inf')
        
        # Current price above EMA200
        current_above = data.close[-1] > data.ema200[-1]
        
        # Was below recently
        was_below = min_close < min_ema200
        
        reclaim = was_below and current_above
        
        logger.debug(f"Reclaim pattern: {'✓' if reclaim else '✗'}")
        return reclaim
    
    def _check_ema_expansion(self, data: IndicatorData) -> tuple[bool, float]:
        """
        Check EMA expansion (early trend detector)
        Measures spread between EMA50 and EMA200
        
        Returns:
            (expanding: bool, spread: float)
        """
        if not data.ema50 or not data.ema200:
            return False, 0.0
        
        ema50_current = data.ema50[-1]
        ema200_current = data.ema200[-1]
        
        # Calculate percentage spread
        if ema200_current == 0:
            return False, 0.0
        
        spread = (ema50_current - ema200_current) / ema200_current
        expansion_threshold = self.config['expansion_threshold']
        expanding = spread > expansion_threshold
        
        logger.debug(
            f"EMA expansion: {spread:.4f} ({spread*100:.2f}%) "
            f"(threshold: {expansion_threshold*100:.2f}%) - {'✓' if expanding else '✗'}"
        )
        return expanding, spread
    
    def _check_slope_filter(
        self, 
        data: IndicatorData, 
        cross_event: CrossEvent
    ) -> tuple[bool, float]:
        """
        Check EMA200 slope filter - SIMPLIFIED
        Compare current EMA200 to EMA200 at cross
        
        Args:
            data: Indicator data
            cross_event: Cross event with cross_index
            
        Returns:
            (slope_rising: bool, slope_change: float)
        """
        cross_index = cross_event.cross_index
        current_index = len(data.ema200) - 1
        
        # Validation
        if cross_index >= len(data.ema200) or current_index < 0:
            logger.debug("Invalid indices for slope check")
            return False, 0.0
        
        if not data.ema200 or len(data.ema200) < cross_index + 1:
            logger.debug("Insufficient EMA200 data for slope check")
            return False, 0.0
        
        # Simple: Is EMA200 now higher than at cross?
        ema200_at_cross = data.ema200[cross_index]
        ema200_now = data.ema200[current_index]
        
        if ema200_at_cross == 0:
            return False, 0.0
        
        # Check if rising
        slope_rising = ema200_now > ema200_at_cross
        
        # Calculate percentage change
        slope_change = (ema200_now - ema200_at_cross) / ema200_at_cross
        
        logger.debug(
            f"Slope: EMA200 at cross={ema200_at_cross:.2f}, "
            f"now={ema200_now:.2f}, change={slope_change*100:.3f}% "
            f"{'✓ Rising' if slope_rising else '✗ Falling'}"
        )
        
        return slope_rising, slope_change
    
    def _calculate_volume_score(self, data: IndicatorData, cross_event: CrossEvent) -> tuple[int, float]:
        """
        Calculate volume AT CROSS TIME (not current) - COMPULSORY (must be >= 3x)
        
        Checks volume in window around cross (±2 candles) vs baseline before cross
        
        Args:
            data: Indicator data
            cross_event: Cross event with cross_index
            
        Returns:
            (volume_score: int, volume_ratio: float)
            volume_score: 1 if >= 3x at cross, 0 if below
        """
        cross_index = cross_event.cross_index
        cross_window = self.config['volume_cross_window']  # ±2 candles
        baseline_period = self.config['volume_baseline_period']  # 20 candles
        min_ratio = self.config['volume_min_ratio']  # 3.0x
        
        # Volume around the cross (2 before + cross + 2 after = 5 candles)
        cross_start = max(0, cross_index - cross_window)
        cross_end = min(len(data.volume), cross_index + cross_window + 1)
        volume_at_cross = data.volume[cross_start:cross_end]
        
        if len(volume_at_cross) < 1:
            logger.debug("No volume data at cross")
            return 0, 0.0
        
        # Baseline volume BEFORE cross (20 candles before the cross window)
        baseline_end = cross_start
        baseline_start = max(0, baseline_end - baseline_period)
        volume_baseline = data.volume[baseline_start:baseline_end]
        
        if len(volume_baseline) < baseline_period // 2:
            logger.debug(f"Insufficient baseline volume data: {len(volume_baseline)} candles")
            return 0, 0.0
        
        # Calculate averages
        avg_cross = sum(volume_at_cross) / len(volume_at_cross)
        avg_baseline = sum(volume_baseline) / len(volume_baseline)
        
        if avg_baseline == 0:
            return 0, 0.0
        
        # Calculate ratio
        ratio = avg_cross / avg_baseline
        
        # Score: 1 if meets 3x requirement (COMPULSORY)
        score = 1 if ratio >= min_ratio else 0
        
        logger.debug(
            f"Volume at cross: candles [{cross_start}:{cross_end}] "
            f"avg={avg_cross:.0f}, baseline={avg_baseline:.0f}, "
            f"ratio={ratio:.2f}x (minimum: {min_ratio}x) {'✓' if score == 1 else '✗'}"
        )
        return score, ratio
    
    def calculate_feature_summary(self, features: SignalFeatures) -> dict:
        """
        Generate human-readable summary of features
        
        Args:
            features: SignalFeatures object
            
        Returns:
            Dictionary with summary
        """
        return {
            'Trend Strength': f"{'✓' if features.trend_ok else '✗'} ADX 15m: {features.adx_value_15m:.1f} | 1h: {features.adx_value_1h:.1f}",
            'Momentum': f"{'✓' if features.momentum_ok else '✗'} RSI 15m: {features.rsi_value_15m:.1f} | 1h: {features.rsi_value_1h:.1f}",
            'Structure': f"{'✓' if features.structure_ok else '✗'} Holds: {features.hold_count}/5",
            'Reclaim': '✓ Yes' if features.reclaim else '✗ No',
            'EMA Expansion': f"{'✓' if features.expanding else '✗'} {features.expansion_spread*100:.2f}%",
            'EMA200 Slope': f"{'✓ Rising' if features.slope_rising else '✗ Falling'} {features.slope_ratio*100:.2f}%",
            'Volume': f"Score: {features.volume_score}/2 (ratio: {features.volume_ratio:.2f}x)",
        }
