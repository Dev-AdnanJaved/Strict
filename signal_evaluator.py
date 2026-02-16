"""
Signal Evaluator Module
Orchestrates the complete signal evaluation process
"""
from typing import Optional, Tuple
from models import (
    IndicatorData, CrossEvent, SignalFeatures, 
    Signal, RegimeState
)
from cross_detector import CrossDetector
from feature_calculator import FeatureCalculator
from scoring_engine import ScoringEngine
from config import SIGNAL_CONFIG
import logging

logger = logging.getLogger(__name__)


class SignalEvaluator:
    """
    Main signal evaluation orchestrator
    Coordinates cross detection, feature calculation, and scoring
    """
    
    def __init__(self):
        """Initialize signal evaluator with all components"""
        self.cross_detector = CrossDetector(
            fast_ema=SIGNAL_CONFIG['cross_emas'][0],
            slow_ema=SIGNAL_CONFIG['cross_emas'][1]
        )
        self.feature_calculator = FeatureCalculator(SIGNAL_CONFIG)
        self.scoring_engine = ScoringEngine()
        self.evaluation_window = SIGNAL_CONFIG['evaluation_window']
        self.cross_lookback = SIGNAL_CONFIG.get('cross_lookback', 5)  # Default 5 candles
    
    def evaluate(
        self,
        symbol: str,
        timeframe: str,
        data_15m: IndicatorData,
        data_1h: IndicatorData,
        regime_state: RegimeState
    ) -> Tuple[Optional[Signal], RegimeState]:
        """
        Complete signal evaluation workflow - ALL CRITERIA NOW COMPULSORY
        
        STEP 1: Detect cross event (on 15m)
        STEP 2: Monitor evaluation window
        STEP 3: Compute features (using BOTH 15m and 1h data)
        STEP 4: Check ALL criteria pass (no time wait - checks immediately)
        
        Args:
            symbol: Trading pair symbol
            timeframe: Timeframe string (should be 15m)
            data_15m: Indicator data for 15m timeframe
            data_1h: Indicator data for 1h timeframe
            regime_state: Current regime state for this symbol-timeframe
            
        Returns:
            (Signal object or None, Updated RegimeState)
        """
        current_index = len(data_15m.close) - 1
        
        # STEP 1: Detect Cross Event (check last N candles to catch any missed crosses)
        new_cross = self.cross_detector.detect_cross(
            symbol, timeframe, data_15m, lookback=self.cross_lookback
        )
        
        if new_cross and new_cross.cross_type == 'bullish':
            logger.info(f"New bullish cross: {symbol} {timeframe}")
            regime_state.set_cross(new_cross)
            regime_state.last_check_index = current_index
        
        # STEP 2 & 3: Check if we should evaluate
        if not regime_state.should_evaluate(current_index, self.evaluation_window):
            # No active cross or outside window
            if regime_state.active_cross:
                candles_since = regime_state.active_cross.candles_since_cross(current_index)
                if candles_since > self.evaluation_window:
                    logger.info(
                        f"Window expired for {symbol} {timeframe} "
                        f"({candles_since} candles since cross)"
                    )
                    regime_state.reset()
            return None, regime_state
        
        # We have an active cross within the window
        cross_event = regime_state.active_cross
        candles_since = cross_event.candles_since_cross(current_index)
        
        logger.info(
            f"Evaluating {symbol} {timeframe} - "
            f"{candles_since}/{self.evaluation_window} candles since cross"
        )
        
        # STEP 3: Compute Features (USING BOTH TIMEFRAMES)
        logger.debug("Computing features with multi-timeframe data...")
        features = self.feature_calculator.calculate_all_features(data_15m, data_1h, cross_event)
        
        # Log feature summary
        feature_summary = self.feature_calculator.calculate_feature_summary(features)
        for key, value in feature_summary.items():
            logger.debug(f"  {key}: {value}")
        
        # STEP 4: Check ALL CRITERIA PASS (COMPULSORY - NO TIME WAIT)
        # First: Basic sanity check - current price must be above EMA200
        current_price = data_15m.close[-1]
        current_ema200 = data_15m.ema200[-1]
        
        if current_price <= current_ema200:
            logger.info(
                f"Signal REJECTED for {symbol} {timeframe} - "
                f"Price ${current_price:.2f} below EMA200 ${current_ema200:.2f}"
            )
            return None, regime_state
        
        # Then: Check all other compulsory criteria
        all_criteria_met = (
            features.trend_ok and          # ADX on both timeframes
            features.momentum_ok and       # RSI on both timeframes
            # features.structure_ok and    # REMOVED - not compulsory anymore
            # features.reclaim and         # REMOVED - not compulsory anymore
            features.expanding and         # EMAs expanding
            features.slope_rising and      # EMA200 slope rising
            features.volume_score == 1     # Volume >= 1.2x
        )
        
        if not all_criteria_met:
            logger.info(f"Signal REJECTED for {symbol} {timeframe} - Not all criteria met:")
            logger.info(f"  Price Check: ${current_price:.2f} > ${current_ema200:.2f} ✓")
            logger.info(f"  Trend (ADX): {'✓' if features.trend_ok else '✗ FAILED'}")
            logger.info(f"  Momentum (RSI): {'✓' if features.momentum_ok else '✗ FAILED'}")
            logger.info(f"  Structure: {'✓' if features.structure_ok else '(optional)'}")
            logger.info(f"  Reclaim: {'✓' if features.reclaim else '(optional)'}")
            logger.info(f"  Expanding: {'✓' if features.expanding else '✗ FAILED'}")
            logger.info(f"  Slope Rising: {'✓' if features.slope_rising else '✗ FAILED'}")
            logger.info(f"  Volume: {'✓' if features.volume_score == 1 else '✗ FAILED'}")
            return None, regime_state
        
        # ALL CRITERIA MET! Create signal
        logger.info(f"✅ ALL CRITERIA MET for {symbol} {timeframe}!")
        logger.info(f"   Price: ${current_price:.2f} | EMA200: ${current_ema200:.2f}")
        
        signal = Signal(
            symbol=symbol,
            timeframe=timeframe,
            signal_type='confirmed',
            score=10,  # Doesn't matter anymore, all pass = signal sent
            max_score=10,
            features=features,
            cross_event=cross_event
        )
        
        # Add price and ema200 to signal for Telegram message
        signal.current_price = current_price
        signal.current_ema200 = current_ema200
        
        # Update regime state last check
        regime_state.last_check_index = current_index
        
        return signal, regime_state
    
    def should_alert(
        self, 
        signal: Signal, 
        regime_state: RegimeState
    ) -> Tuple[bool, str]:
        """
        Determine if an alert should be sent
        Since ALL criteria are now compulsory, if signal exists = send alert
        
        Args:
            signal: Evaluated signal
            regime_state: Current regime state
            
        Returns:
            (should_send: bool, alert_type: str)
        """
        if not signal:
            return False, 'none'
        
        # If we have a signal, ALL criteria were met - send it!
        if not regime_state.sent_confirmed_alert:
            return True, 'confirmed'
        
        return False, 'none'
    
    def process_candle_update(
        self,
        symbol: str,
        timeframe: str,
        data_15m: IndicatorData,
        data_1h: IndicatorData,
        regime_state: RegimeState
    ) -> Tuple[Optional[Signal], bool, str, RegimeState]:
        """
        Process a new candle update
        Complete workflow from detection to alert decision
        
        Args:
            symbol: Trading pair symbol
            timeframe: Timeframe string (15m)
            data_15m: Updated 15m indicator data
            data_1h: Updated 1h indicator data
            regime_state: Current regime state
            
        Returns:
            (signal: Signal or None, 
             should_alert: bool, 
             alert_type: str,
             updated_regime_state: RegimeState)
        """
        # Evaluate signal with both timeframes
        signal, updated_state = self.evaluate(
            symbol, timeframe, data_15m, data_1h, regime_state
        )
        
        # Determine if should alert (only confirmed now)
        should_send, alert_type = self.should_alert(signal, updated_state)
        
        # Update regime state alert flags
        if should_send and alert_type == 'confirmed':
            updated_state.sent_confirmed_alert = True
            logger.info(f"📨 CONFIRMED ALERT triggered: {symbol} {timeframe}")
        
        return signal, should_send, alert_type, updated_state
    
    def get_evaluation_status(
        self, 
        regime_state: RegimeState,
        current_data_length: int
    ) -> dict:
        """
        Get current evaluation status for a regime
        
        Args:
            regime_state: Current regime state
            current_data_length: Current length of data
            
        Returns:
            Status dictionary
        """
        if not regime_state.active_cross:
            return {
                'status': 'waiting',
                'active_cross': False,
                'message': 'Waiting for cross event'
            }
        
        current_index = current_data_length - 1
        candles_since = regime_state.active_cross.candles_since_cross(current_index)
        remaining = self.evaluation_window - candles_since
        
        if remaining > 0:
            return {
                'status': 'evaluating',
                'active_cross': True,
                'candles_since_cross': candles_since,
                'candles_remaining': remaining,
                'window_size': self.evaluation_window,
                'early_alert_sent': regime_state.sent_early_alert,
                'confirmed_alert_sent': regime_state.sent_confirmed_alert,
                'message': f'Evaluating ({candles_since}/{self.evaluation_window} candles)'
            }
        else:
            return {
                'status': 'expired',
                'active_cross': True,
                'candles_since_cross': candles_since,
                'message': 'Evaluation window expired'
            }
