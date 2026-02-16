"""
Scoring Engine Module
NOTE: Scoring is now deprecated - ALL criteria are COMPULSORY
Keeping this file for compatibility but it's not used for decisions anymore
"""
from models import SignalFeatures, Signal, CrossEvent
import logging

logger = logging.getLogger(__name__)


class ScoringEngine:
    """
    Scoring engine - now deprecated
    All criteria are COMPULSORY, no scoring system
    """
    
    def __init__(self, scoring_config: dict = None):
        """Initialize scoring engine"""
        pass
    
    def create_signal(
        self,
        symbol: str,
        timeframe: str,
        features: SignalFeatures,
        cross_event: CrossEvent,
        score: int = 10
    ) -> Signal:
        """
        Create Signal object (score not used anymore)
        """
        return Signal(
            symbol=symbol,
            timeframe=timeframe,
            signal_type='confirmed',
            score=10,  # Not used
            max_score=10,
            features=features,
            cross_event=cross_event
        )
    
    def should_send_confirmed_alert(self, score: int = None) -> bool:
        """Always return True - not used anymore"""
        return True
    
    def get_score_breakdown(self, features: SignalFeatures) -> dict:
        """
        Get detailed breakdown of score components
        
        Args:
            features: SignalFeatures object
            
        Returns:
            Dictionary with score breakdown
        """
        breakdown = {}
        
        breakdown['cross_base'] = {
            'score': self.config['cross_base'],
            'active': True,
            'description': 'EMA cross detected'
        }
        
        breakdown['trend'] = {
            'score': self.config['trend_ok'] if features.trend_ok else 0,
            'active': features.trend_ok,
            'description': f"ADX 15m: {features.adx_value_15m:.1f} (>25) | 1h: {features.adx_value_1h:.1f} (>22)"
        }
        
        breakdown['slope'] = {
            'score': self.config['slope_rising'] if features.slope_rising else 0,
            'active': features.slope_rising,
            'description': f"EMA200 slope rising ({features.slope_ratio*100:.2f}%)"
        }
        
        breakdown['momentum'] = {
            'score': self.config['momentum_ok'] if features.momentum_ok else 0,
            'active': features.momentum_ok,
            'description': f"RSI 15m: {features.rsi_value_15m:.1f} (>50) | 1h: {features.rsi_value_1h:.1f} (>50)"
        }
        
        breakdown['structure'] = {
            'score': self.config['structure_ok'] if features.structure_ok else 0,
            'active': features.structure_ok,
            'description': f"Price holding ({features.hold_count}/5 candles)"
        }
        
        breakdown['reclaim'] = {
            'score': self.config['reclaim'] if features.reclaim else 0,
            'active': features.reclaim,
            'description': 'Reclaim pattern detected'
        }
        
        breakdown['expansion'] = {
            'score': self.config['expanding'] if features.expanding else 0,
            'active': features.expanding,
            'description': f"EMA expansion {features.expansion_spread*100:.2f}%"
        }
        
        breakdown['volume'] = {
            'score': features.volume_score,
            'active': features.volume_score > 0,
            'description': f"Volume ratio {features.volume_ratio:.2f}x"
        }
        
        return breakdown
    
    def format_score_report(self, signal: Signal) -> str:
        """
        Format a human-readable score report
        
        Args:
            signal: Signal object
            
        Returns:
            Formatted string report
        """
        breakdown = self.get_score_breakdown(signal.features)
        
        report = f"\n{'='*50}\n"
        report += f"SCORE REPORT: {signal.symbol} {signal.timeframe}\n"
        report += f"{'='*50}\n"
        report += f"Total Score: {signal.score}/{signal.max_score} ({signal.score_percentage():.1f}%)\n"
        report += f"Signal Type: {signal.signal_type.upper()}\n"
        report += f"\nBreakdown:\n"
        
        for key, item in breakdown.items():
            status = "✓" if item['active'] else "✗"
            report += f"  {status} {item['description']}: +{item['score']}\n"
        
        report += f"{'='*50}\n"
        
        return report
