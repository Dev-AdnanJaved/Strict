"""
Main Bot Runner
Complete automated trading signal bot
"""
import os
import time
import logging
from datetime import datetime
from typing import List
import sys

from config import (
    BINANCE_CONFIG, SYMBOL_CONFIG, TIMEFRAMES,
    TELEGRAM_CONFIG, LOGGING_CONFIG
)
from binance_client import BinanceClient
from market_data_manager import MarketDataManager
from trading_bot import TradingBot

# Setup logging
logging.basicConfig(
    level=getattr(logging, LOGGING_CONFIG.get('level', 'INFO')),
    format=LOGGING_CONFIG.get('format', '%(asctime)s - %(name)s - %(levelname)s - %(message)s'),
    handlers=[
        logging.FileHandler(LOGGING_CONFIG.get('file', 'trading_bot.log')),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


class BotRunner:
    """
    Main bot runner - orchestrates the complete system
    """
    
    def __init__(
        self,
        run_interval: int = 60  # seconds between checks
    ):
        """
        Initialize bot runner
        
        Args:
            run_interval: Seconds between each check (default: 60)
        """
        self.run_interval = run_interval
        # Always use 15m for crosses, 1h for confirmation
        self.timeframes = ['15m', '1h']
        
        # Initialize Binance client
        logger.info("Initializing Binance client...")
        self.binance_client = BinanceClient(
            api_key=BINANCE_CONFIG.get('api_key'),
            api_secret=BINANCE_CONFIG.get('api_secret')
        )
        
        # Test connection
        if not self.binance_client.test_connectivity():
            logger.error("Failed to connect to Binance API")
            sys.exit(1)
        
        # Initialize market data manager
        self.market_manager = MarketDataManager(self.binance_client)
        
        # Get symbols to monitor
        self.symbols = self._get_symbols_to_monitor()
        
        if not self.symbols:
            logger.error("No symbols to monitor!")
            sys.exit(1)
        
        logger.info(f"Monitoring {len(self.symbols)} symbols: {', '.join(self.symbols[:5])}...")
        logger.info(f"Timeframes: {', '.join(self.timeframes)}")
        
        # Initialize trading bot
        telegram_enabled = bool(TELEGRAM_CONFIG.get('bot_token'))
        self.trading_bot = TradingBot(
            symbols=self.symbols,
            timeframes=self.timeframes,
            enable_telegram=telegram_enabled
        )
        
        # Test Telegram if enabled
        if telegram_enabled:
            if self.trading_bot.test_telegram():
                logger.info("Telegram notifications enabled")
            else:
                logger.warning("Telegram test failed - check credentials")
        else:
            logger.warning("Telegram not configured - running without notifications")
        
        # Statistics
        self.stats = {
            'start_time': datetime.now(),
            'total_runs': 0,
            'total_symbols_processed': 0,
            'total_alerts_sent': 0,
            'errors': 0,
            'last_run': None
        }
    
    def _get_symbols_to_monitor(self) -> List[str]:
        """
        Get list of symbols to monitor based on configuration
        
        Returns:
            List of symbols
        """
        mode = SYMBOL_CONFIG.get('mode', 'top_volume')
        
        if mode == 'custom':
            symbols = SYMBOL_CONFIG.get('custom_symbols', [])
            logger.info(f"Using custom symbols: {symbols}")
            return symbols
        
        elif mode == 'all':
            logger.info("Fetching all USDT futures pairs...")
            symbols = self.binance_client.get_all_symbols()
            
            # Apply volume filter if set
            min_volume = SYMBOL_CONFIG.get('min_volume_filter', 0)
            if min_volume > 0:
                symbols = self._filter_by_volume(symbols, min_volume)
            
            return symbols
        
        elif mode == 'top_volume':
            top_n = SYMBOL_CONFIG.get('top_n_coins', 20)
            
            if top_n is None:
                logger.info("Fetching all symbols by volume...")
                symbols = self.binance_client.get_all_symbols()
                symbols = self._filter_by_volume(symbols, 0)  # Sort by volume
                return symbols
            else:
                logger.info(f"Fetching top {top_n} symbols by volume...")
                return self.binance_client.get_top_volume_symbols(top_n)
        
        else:
            logger.error(f"Unknown symbol mode: {mode}")
            return []
    
    def _filter_by_volume(self, symbols: List[str], min_volume: float) -> List[str]:
        """Filter symbols by 24h volume"""
        logger.info(f"Filtering symbols by volume (min: ${min_volume:,.0f})...")
        
        ticker_data = self.binance_client.get_ticker_24h()
        
        # Create volume map
        volume_map = {
            t['symbol']: float(t['quoteVolume'])
            for t in ticker_data
            if t['symbol'] in symbols
        }
        
        # Filter and sort
        filtered = [
            symbol for symbol in symbols
            if volume_map.get(symbol, 0) >= min_volume
        ]
        
        filtered.sort(key=lambda s: volume_map.get(s, 0), reverse=True)
        
        logger.info(f"Filtered to {len(filtered)} symbols meeting volume criteria")
        return filtered
    
    def run_once(self):
        """
        Run one iteration of the bot
        Fetch data, process signals, send alerts
        """
        self.stats['total_runs'] += 1
        self.stats['last_run'] = datetime.now()
        
        logger.info("="*60)
        logger.info(f"Starting run #{self.stats['total_runs']} at {datetime.now()}")
        logger.info("="*60)
        
        try:
            # Fetch market data for all symbols
            logger.info(f"Fetching data for {len(self.symbols)} symbols...")
            
            all_market_data = self.market_manager.fetch_multiple_symbols(
                self.symbols,
                self.timeframes,
                limit=500
            )
            
            if not all_market_data:
                logger.warning("No market data fetched!")
                return
            
            self.stats['total_symbols_processed'] += len(all_market_data)
            
            # Process all updates through trading bot
            logger.info("Processing signals...")
            results = self.trading_bot.process_all_updates(all_market_data)
            
            # Log results
            if results:
                self.stats['total_alerts_sent'] += len(results)
                logger.info(f"{len(results)} alerts sent:")
                for result in results:
                    logger.info(
                        f"  Alert: {result['symbol']} {result['timeframe']}: "
                        f"{result['alert_type'].upper()} (score: {result['score']})"
                    )
            else:
                logger.info("No alerts triggered this run")
            
            # Log bot status summary
            logger.info(self._get_status_summary())
            
        except Exception as e:
            self.stats['errors'] += 1
            logger.error(f"Error in run: {e}", exc_info=True)
    
    def run_continuous(self):
        """
        Run bot continuously with configured interval
        """
        logger.info("="*60)
        logger.info("TRADING BOT STARTED")
        logger.info("="*60)
        logger.info(f"Symbols: {len(self.symbols)}")
        logger.info(f"Monitoring: 15m for crosses, 1h for confirmation")
        logger.info(f"Check interval: {self.run_interval}s")
        logger.info("="*60)
        
        # Send startup notification
        if self.trading_bot.telegram.enabled:
            self.trading_bot.telegram.send_custom_message(
                "Trading Bot Started",
                {
                    "Symbols": f"{len(self.symbols)} pairs",
                    "Mode": "15m crosses + 1h confirmation",
                    "Interval": f"{self.run_interval}s",
                    "Started": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
            )
        
        try:
            while True:
                self.run_once()
                
                # Wait for next iteration
                logger.info(f"\nWaiting {self.run_interval}s until next check...\n")
                time.sleep(self.run_interval)
                
        except KeyboardInterrupt:
            logger.info("\n" + "="*60)
            logger.info("Bot stopped by user")
            logger.info("="*60)
            self._print_final_stats()
            
            # Send shutdown notification
            if self.trading_bot.telegram.enabled:
                self.trading_bot.telegram.send_custom_message(
                    "Trading Bot Stopped",
                    {
                        "Total Runs": self.stats['total_runs'],
                        "Alerts Sent": self.stats['total_alerts_sent'],
                        "Runtime": str(datetime.now() - self.stats['start_time']).split('.')[0]
                    }
                )
        
        except Exception as e:
            logger.error(f"Fatal error: {e}", exc_info=True)
            
            # Send error notification
            if self.trading_bot.telegram.enabled:
                self.trading_bot.telegram.send_error(
                    f"Fatal error: {str(e)}",
                    {"Time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
                )
    
    def _get_status_summary(self) -> str:
        """Get brief status summary"""
        runtime = datetime.now() - self.stats['start_time']
        
        return (
            f"\nStatus: Run #{self.stats['total_runs']} | "
            f"Alerts: {self.stats['total_alerts_sent']} | "
            f"Errors: {self.stats['errors']} | "
            f"Runtime: {str(runtime).split('.')[0]}"
        )
    
    def _print_final_stats(self):
        """Print final statistics"""
        runtime = datetime.now() - self.stats['start_time']
        
        print("\n" + "="*60)
        print("FINAL STATISTICS")
        print("="*60)
        print(f"Start Time: {self.stats['start_time'].strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"End Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Runtime: {str(runtime).split('.')[0]}")
        print(f"Total Runs: {self.stats['total_runs']}")
        print(f"Symbols Processed: {self.stats['total_symbols_processed']}")
        print(f"Alerts Sent: {self.stats['total_alerts_sent']}")
        print(f"Errors: {self.stats['errors']}")
        print("="*60)


def main():
    """
    Main entry point
    """
    # Check environment variables
    if not os.getenv('TELEGRAM_BOT_TOKEN'):
        logger.warning(
            "TELEGRAM_BOT_TOKEN not set in environment. "
            "Bot will run without notifications."
        )
    
    if not os.getenv('TELEGRAM_CHAT_ID'):
        logger.warning(
            "TELEGRAM_CHAT_ID not set in environment. "
            "Bot will run without notifications."
        )
    
    # Create and run bot
    runner = BotRunner(
        run_interval=60  # Check every 60 seconds
    )
    
    # Run continuously
    runner.run_continuous()


if __name__ == "__main__":
    main()
