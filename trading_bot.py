"""
Main Trading Bot
Orchestrates all components for signal detection and alerting
"""
from typing import Dict, List, Optional
from models import MarketData, IndicatorData
from signal_evaluator import SignalEvaluator
from telegram_notifier import TelegramNotifier
from regime_tracker import RegimeTracker
from config import TIMEFRAMES, TELEGRAM_CONFIG
import logging

logger = logging.getLogger(__name__)


class TradingBot:
    """
    Main trading bot class
    Coordinates signal evaluation across multiple symbols and timeframes
    """
    
    def __init__(
        self,
        symbols: List[str],
        timeframes: List[str] = None,
        enable_telegram: bool = True
    ):
        """
        Initialize trading bot
        
        Args:
            symbols: List of symbols to monitor
            timeframes: List of timeframes (defaults to config)
            enable_telegram: Enable Telegram notifications
        """
        self.symbols = [s.upper() for s in symbols]
        self.timeframes = timeframes or TIMEFRAMES
        
        # Initialize components
        self.signal_evaluator = SignalEvaluator()
        self.regime_tracker = RegimeTracker()
        self.telegram = TelegramNotifier(enabled=enable_telegram)
        
        # Market data storage
        self.market_data: Dict[str, MarketData] = {}
        
        # Statistics
        self.stats = {
            'total_evaluations': 0,
            'crosses_detected': 0,
            'confirmed_alerts_sent': 0,
            'signals_by_symbol': {},
            'signals_by_timeframe': {}
        }
        
        logger.info(f"Trading bot initialized for {len(self.symbols)} symbols")
        logger.info(f"Monitoring timeframes: {', '.join(self.timeframes)}")
    
    def update_market_data(
        self,
        symbol: str,
        timeframe: str,
        indicator_data: IndicatorData
    ):
        """
        Update market data for a symbol-timeframe pair
        
        Args:
            symbol: Trading pair symbol
            timeframe: Timeframe string
            indicator_data: New indicator data
        """
        symbol = symbol.upper()
        
        # Initialize market data for symbol if needed
        if symbol not in self.market_data:
            self.market_data[symbol] = MarketData(symbol=symbol)
        
        # Update timeframe data
        self.market_data[symbol].add_timeframe(timeframe, indicator_data)
        logger.debug(f"Updated market data: {symbol} {timeframe} ({len(indicator_data)} candles)")
    
    def process_update(
        self,
        symbol: str,
        timeframe: str,
        indicator_data_15m: IndicatorData,
        indicator_data_1h: IndicatorData
    ) -> Optional[Dict]:
        """
        Process a market data update with multi-timeframe data
        Complete workflow from data update to potential alert
        
        Args:
            symbol: Trading pair symbol
            timeframe: Timeframe string (should be '15m')
            indicator_data_15m: Updated 15m indicator data
            indicator_data_1h: Updated 1h indicator data
            
        Returns:
            Result dictionary with signal info if alert sent
        """
        symbol = symbol.upper()
        
        # Update market data for both timeframes
        self.update_market_data(symbol, '15m', indicator_data_15m)
        self.update_market_data(symbol, '1h', indicator_data_1h)
        
        # Get current regime state
        regime_state = self.regime_tracker.get_regime(symbol, timeframe)
        
        # Process the update with both timeframes
        signal, should_alert, alert_type, updated_state = (
            self.signal_evaluator.process_candle_update(
                symbol, timeframe, indicator_data_15m, indicator_data_1h, regime_state
            )
        )
        
        # Update regime state
        self.regime_tracker.update_regime(symbol, timeframe, updated_state)
        
        # Update statistics
        self.stats['total_evaluations'] += 1
        
        if signal:
            # Track by symbol
            if symbol not in self.stats['signals_by_symbol']:
                self.stats['signals_by_symbol'][symbol] = 0
            self.stats['signals_by_symbol'][symbol] += 1
            
            # Track by timeframe
            if timeframe not in self.stats['signals_by_timeframe']:
                self.stats['signals_by_timeframe'][timeframe] = 0
            self.stats['signals_by_timeframe'][timeframe] += 1
        
        # Send alert if needed (only confirmed now)
        if should_alert:
            alert_sent = self.telegram.send_alert(signal, alert_type)
            
            if alert_sent:
                self.stats['confirmed_alerts_sent'] += 1
                
                logger.info(
                    f"{alert_type.upper()} alert sent: "
                    f"{symbol} {timeframe} (Score: {signal.score})"
                )
                
                return {
                    'symbol': symbol,
                    'timeframe': timeframe,
                    'alert_type': alert_type,
                    'score': signal.score,
                    'signal': signal.to_dict()
                }
        
        return None
    
    def process_all_updates(self, market_data_dict: Dict[str, Dict[str, IndicatorData]]):
        """
        Process updates for all symbols
        Expects market_data_dict with both '15m' and '1h' data for each symbol
        
        Args:
            market_data_dict: {symbol: {'15m': IndicatorData, '1h': IndicatorData}}
        """
        results = []
        
        for symbol in market_data_dict:
            # Check if both timeframes present
            if '15m' not in market_data_dict[symbol] or '1h' not in market_data_dict[symbol]:
                logger.warning(f"Missing required timeframes for {symbol} (need both 15m and 1h)")
                continue
            
            data_15m = market_data_dict[symbol]['15m']
            data_1h = market_data_dict[symbol]['1h']
            
            result = self.process_update(symbol, '15m', data_15m, data_1h)
            if result:
                results.append(result)
        
        return results
    
    def get_status(self, symbol: str = None) -> Dict:
        """
        Get bot status
        
        Args:
            symbol: Optional symbol filter
            
        Returns:
            Status dictionary
        """
        regime_summary = self.regime_tracker.get_regime_summary(symbol)
        
        status = {
            'symbols_monitored': len(self.symbols),
            'timeframes': self.timeframes,
            'statistics': self.stats,
            'regimes': regime_summary,
            'telegram_enabled': self.telegram.enabled
        }
        
        return status
    
    def get_status_report(self, symbol: str = None) -> str:
        """
        Get formatted status report
        
        Args:
            symbol: Optional symbol filter
            
        Returns:
            Formatted status string
        """
        status = self.get_status(symbol)
        
        report = "\n" + "="*60 + "\n"
        report += "TRADING BOT STATUS REPORT\n"
        report += "="*60 + "\n"
        
        # Bot configuration
        report += "\nCONFIGURATION:\n"
        report += f"  Symbols Monitored: {status['symbols_monitored']}\n"
        report += f"  Timeframes: {', '.join(status['timeframes'])}\n"
        report += f"  Telegram: {'Enabled' if status['telegram_enabled'] else 'Disabled'}\n"
        
        # Statistics
        report += "\nSTATISTICS:\n"
        stats = status['statistics']
        report += f"  Total Evaluations: {stats['total_evaluations']}\n"
        report += f"  Crosses Detected: {stats.get('crosses_detected', 0)}\n"
        report += f"  Confirmed Alerts: {stats['confirmed_alerts_sent']}\n"
        
        # By symbol
        if stats['signals_by_symbol']:
            report += "\n  By Symbol:\n"
            for sym, count in stats['signals_by_symbol'].items():
                report += f"    {sym}: {count} signals\n"
        
        # By timeframe
        if stats['signals_by_timeframe']:
            report += "\n  By Timeframe:\n"
            for tf, count in stats['signals_by_timeframe'].items():
                report += f"    {tf}: {count} signals\n"
        
        # Regime status
        report += "\nACTIVE REGIMES:\n"
        regimes = status['regimes']
        report += f"  Total: {regimes['total_regimes']}\n"
        report += f"  Active Crosses: {regimes['active_crosses']}\n"
        
        if regimes['by_symbol']:
            for sym, sym_data in regimes['by_symbol'].items():
                if sym_data['active'] > 0:
                    report += f"\n  {sym}: {sym_data['active']} active\n"
                    for tf, tf_data in sym_data['timeframes'].items():
                        if tf_data['active_cross']:
                            if tf_data['confirmed_alert_sent']:
                                status_icon = "[CONFIRMED]"
                            elif tf_data['early_alert_sent']:
                                status_icon = "[EARLY]"
                            else:
                                status_icon = "[EVALUATING]"
                            report += f"    {status_icon} {tf}\n"
        
        report += "\n" + "="*60 + "\n"
        
        return report
    
    def reset_symbol(self, symbol: str):
        """
        Reset all regimes for a symbol
        
        Args:
            symbol: Symbol to reset
        """
        self.regime_tracker.reset_all_regimes(symbol.upper())
        logger.info(f"Reset all regimes for {symbol}")
    
    def reset_all(self):
        """Reset all regimes"""
        self.regime_tracker.reset_all_regimes()
        logger.info("Reset all regimes")
    
    def test_telegram(self) -> bool:
        """
        Test Telegram connection
        
        Returns:
            True if successful
        """
        return self.telegram.test_connection()
    
    def send_status_update(self):
        """Send status update to Telegram"""
        status = self.get_status()
        
        status_msg = {
            'Symbols': ', '.join(self.symbols[:5]) + ('...' if len(self.symbols) > 5 else ''),
            'Active Crosses': status['regimes']['active_crosses'],
            'Confirmed Alerts': status['statistics']['confirmed_alerts_sent'],
            'Total Evaluations': status['statistics']['total_evaluations']
        }
        
        self.telegram.send_status_update(status_msg)
