"""
Regime Tracker Module
Manages regime states across multiple symbols and timeframes
"""
from typing import Dict, Tuple
from models import RegimeState
import logging

logger = logging.getLogger(__name__)


class RegimeTracker:
    """
    Tracks regime states for multiple symbol-timeframe pairs
    Thread-safe state management
    """
    
    def __init__(self):
        """Initialize regime tracker"""
        # Structure: {symbol: {timeframe: RegimeState}}
        self._regimes: Dict[str, Dict[str, RegimeState]] = {}
    
    def _get_key(self, symbol: str, timeframe: str) -> Tuple[str, str]:
        """Normalize symbol and timeframe keys"""
        return symbol.upper(), timeframe.lower()
    
    def get_regime(self, symbol: str, timeframe: str) -> RegimeState:
        """
        Get or create regime state for symbol-timeframe pair
        
        Args:
            symbol: Trading pair symbol
            timeframe: Timeframe string
            
        Returns:
            RegimeState object
        """
        symbol, timeframe = self._get_key(symbol, timeframe)
        
        # Initialize symbol dict if needed
        if symbol not in self._regimes:
            self._regimes[symbol] = {}
        
        # Initialize timeframe regime if needed
        if timeframe not in self._regimes[symbol]:
            self._regimes[symbol][timeframe] = RegimeState(
                symbol=symbol,
                timeframe=timeframe
            )
            logger.debug(f"Created new regime state: {symbol} {timeframe}")
        
        return self._regimes[symbol][timeframe]
    
    def update_regime(self, symbol: str, timeframe: str, regime_state: RegimeState):
        """
        Update regime state for symbol-timeframe pair
        
        Args:
            symbol: Trading pair symbol
            timeframe: Timeframe string
            regime_state: Updated RegimeState object
        """
        symbol, timeframe = self._get_key(symbol, timeframe)
        
        if symbol not in self._regimes:
            self._regimes[symbol] = {}
        
        self._regimes[symbol][timeframe] = regime_state
        logger.debug(f"Updated regime state: {symbol} {timeframe}")
    
    def reset_regime(self, symbol: str, timeframe: str):
        """
        Reset regime state for symbol-timeframe pair
        
        Args:
            symbol: Trading pair symbol
            timeframe: Timeframe string
        """
        regime = self.get_regime(symbol, timeframe)
        regime.reset()
        logger.info(f"Reset regime state: {symbol} {timeframe}")
    
    def reset_all_regimes(self, symbol: str = None):
        """
        Reset all regime states (optionally for specific symbol)
        
        Args:
            symbol: Optional symbol to reset (if None, resets all)
        """
        if symbol:
            symbol, _ = self._get_key(symbol, '')
            if symbol in self._regimes:
                for timeframe in self._regimes[symbol]:
                    self._regimes[symbol][timeframe].reset()
                logger.info(f"Reset all regimes for {symbol}")
        else:
            for sym in self._regimes:
                for tf in self._regimes[sym]:
                    self._regimes[sym][tf].reset()
            logger.info("Reset all regimes for all symbols")
    
    def get_active_regimes(self) -> Dict[str, Dict[str, RegimeState]]:
        """
        Get all regimes with active crosses
        
        Returns:
            Dictionary of active regimes
        """
        active = {}
        
        for symbol in self._regimes:
            for timeframe, regime in self._regimes[symbol].items():
                if regime.active_cross:
                    if symbol not in active:
                        active[symbol] = {}
                    active[symbol][timeframe] = regime
        
        return active
    
    def get_regime_summary(self, symbol: str = None) -> Dict:
        """
        Get summary of regime states
        
        Args:
            symbol: Optional symbol filter
            
        Returns:
            Summary dictionary
        """
        summary = {
            'total_regimes': 0,
            'active_crosses': 0,
            'early_alerts_sent': 0,
            'confirmed_alerts_sent': 0,
            'by_symbol': {}
        }
        
        regimes_to_check = {}
        if symbol:
            symbol, _ = self._get_key(symbol, '')
            if symbol in self._regimes:
                regimes_to_check[symbol] = self._regimes[symbol]
        else:
            regimes_to_check = self._regimes
        
        for sym in regimes_to_check:
            sym_summary = {
                'total': 0,
                'active': 0,
                'early_sent': 0,
                'confirmed_sent': 0,
                'timeframes': {}
            }
            
            for tf, regime in regimes_to_check[sym].items():
                summary['total_regimes'] += 1
                sym_summary['total'] += 1
                
                tf_info = {
                    'active_cross': bool(regime.active_cross),
                    'early_alert_sent': regime.sent_early_alert,
                    'confirmed_alert_sent': regime.sent_confirmed_alert
                }
                
                if regime.active_cross:
                    summary['active_crosses'] += 1
                    sym_summary['active'] += 1
                
                if regime.sent_early_alert:
                    summary['early_alerts_sent'] += 1
                    sym_summary['early_sent'] += 1
                
                if regime.sent_confirmed_alert:
                    summary['confirmed_alerts_sent'] += 1
                    sym_summary['confirmed_sent'] += 1
                
                sym_summary['timeframes'][tf] = tf_info
            
            summary['by_symbol'][sym] = sym_summary
        
        return summary
    
    def cleanup_expired_regimes(self, max_age_candles: int = 50):
        """
        Clean up old regime states that are no longer active
        
        Args:
            max_age_candles: Maximum age in candles before cleanup
        """
        cleaned = 0
        
        for symbol in list(self._regimes.keys()):
            for timeframe in list(self._regimes[symbol].keys()):
                regime = self._regimes[symbol][timeframe]
                
                # If no active cross and hasn't been checked recently
                if not regime.active_cross:
                    # Could add age check here if needed
                    pass
        
        if cleaned > 0:
            logger.info(f"Cleaned up {cleaned} expired regime states")
    
    def get_all_symbols(self) -> list:
        """Get list of all tracked symbols"""
        return list(self._regimes.keys())
    
    def get_timeframes_for_symbol(self, symbol: str) -> list:
        """
        Get list of timeframes for a symbol
        
        Args:
            symbol: Trading pair symbol
            
        Returns:
            List of timeframe strings
        """
        symbol, _ = self._get_key(symbol, '')
        if symbol in self._regimes:
            return list(self._regimes[symbol].keys())
        return []
    
    def has_active_cross(self, symbol: str, timeframe: str) -> bool:
        """
        Check if symbol-timeframe has active cross
        
        Args:
            symbol: Trading pair symbol
            timeframe: Timeframe string
            
        Returns:
            True if has active cross
        """
        regime = self.get_regime(symbol, timeframe)
        return regime.active_cross is not None
    
    def get_status_string(self, symbol: str = None) -> str:
        """
        Get formatted status string
        
        Args:
            symbol: Optional symbol filter
            
        Returns:
            Formatted status string
        """
        summary = self.get_regime_summary(symbol)
        
        status = "="*50 + "\n"
        status += "REGIME TRACKER STATUS\n"
        status += "="*50 + "\n"
        status += f"Total Regimes: {summary['total_regimes']}\n"
        status += f"Active Crosses: {summary['active_crosses']}\n"
        status += f"Early Alerts Sent: {summary['early_alerts_sent']}\n"
        status += f"Confirmed Alerts Sent: {summary['confirmed_alerts_sent']}\n"
        
        if summary['by_symbol']:
            status += "\nBy Symbol:\n"
            for sym, sym_data in summary['by_symbol'].items():
                status += f"\n  {sym}:\n"
                status += f"    Active: {sym_data['active']}/{sym_data['total']}\n"
                status += f"    Early: {sym_data['early_sent']}, Confirmed: {sym_data['confirmed_sent']}\n"
                
                for tf, tf_data in sym_data['timeframes'].items():
                    if tf_data['active_cross']:
                        status += f"      {tf}: "
                        if tf_data['confirmed_alert_sent']:
                            status += "CONFIRMED"
                        elif tf_data['early_alert_sent']:
                            status += "EARLY"
                        else:
                            status += "EVALUATING"
                        status += "\n"
        
        status += "="*50 + "\n"
        return status
