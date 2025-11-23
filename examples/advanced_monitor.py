#!/usr/bin/env python
# btc_price_agent/advanced_monitor.py

import os
import sys
import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import requests
import json

# Add parent directory to path
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

# Import SpoonAI components
from spoon_ai.chat import ChatBot, Memory
from spoon_ai.schema import Message
from spoon_ai.monitoring.clients.base import DataClient
from spoon_ai.monitoring.clients.cex import get_cex_client

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()]
)

logger = logging.getLogger("btc-advanced-monitor")

class BTCAdvancedMonitor:
    """Advanced Bitcoin price monitoring with trend analysis using LLM"""
    
    def __init__(
        self,
        #llm_provider: str = "anthropic",
        #model_name: str = "claude-3-7-sonnet-20250219",
        llm_provider: str = "openai",
        model_name: str = "gpt-4.1",
        market: str = "cex",
        provider: str = "binance",
        symbol: str = "BTCUSDT"
    ):
        # Initialize ChatBot
        self.chatbot = ChatBot(
            llm_provider=llm_provider,
            model_name=model_name,
            api_key=os.getenv("ANTHROPIC_API_KEY") if llm_provider == "anthropic" else os.getenv("OPENAI_API_KEY")
        )
        
        # Initialize memory
        self.memory = Memory()
        
        # Initialize data client
        self.client = get_cex_client(provider)
        self.market = market
        self.provider = provider
        self.symbol = symbol
        
        # System message
        self.system_message = """You are a professional cryptocurrency market analyst, skilled in technical analysis and market trend forecasting.
        You need to analyze the Bitcoin market conditions and provide insights based on the price and trading data provided.
        The analysis should include:
        1. Price trends and momentum
        2. Key support and resistance levels
        3. Volume analysis
        4. Market cycle positioning
        5. Short-term price movement prediction
        
        Please use professional but understandable language, avoid overly complex terminology, and try to provide specific price levels and percentages.
        """
        
        logger.info(f"BTC advanced analysis monitor initialized, using {provider} data source for {symbol}")
    
    async def get_market_data(self) -> Dict[str, Any]:
        """Get market data including current price, 24h statistics and kline data"""
        try:
            # Get current price
            price_data = self.client.get_ticker_price(self.symbol)
            
            # Get 24h statistics
            stats_24h = self.client.get_ticker_24h(self.symbol)
            
            # Get kline data (7 daily candles)
            klines = self.client.get_klines(self.symbol, "1d", 7)
            
            # Format kline data
            formatted_klines = []
            for k in klines:
                formatted_klines.append({
                    "open_time": datetime.fromtimestamp(k[0]/1000).strftime("%Y-%m-%d"),
                    "open": float(k[1]),
                    "high": float(k[2]),
                    "low": float(k[3]),
                    "close": float(k[4]),
                    "volume": float(k[5]),
                })
            
            # Return integrated data
            return {
                "current_price": float(price_data["price"]),
                "price_change_24h": float(stats_24h["priceChange"]),
                "price_change_percent_24h": float(stats_24h["priceChangePercent"]),
                "volume_24h": float(stats_24h["volume"]),
                "high_24h": float(stats_24h["highPrice"]),
                "low_24h": float(stats_24h["lowPrice"]),
                "klines_daily": formatted_klines,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
        except Exception as e:
            logger.error(f"Error getting market data: {str(e)}")
            raise
    
    async def get_market_sentiment(self) -> Dict[str, Any]:
        """Get market sentiment data (can be obtained from external API or using simple heuristic methods)"""
        try:
            # This is a simple heuristic method, in real applications, external APIs can be integrated
            market_data = await self.get_market_data()
            
            # Calculate simple sentiment score based on price change
            price_change = market_data["price_change_percent_24h"]
            
            # Simple sentiment score calculation
            if price_change > 5:
                sentiment = "Extremely Bullish"
                score = 90
            elif price_change > 2:
                sentiment = "Bullish"
                score = 70
            elif price_change > 0:
                sentiment = "Slightly Bullish"
                score = 60
            elif price_change > -2:
                sentiment = "Slightly Bearish"
                score = 40
            elif price_change > -5:
                sentiment = "Bearish"
                score = 30
            else:
                sentiment = "Extremely Bearish"
                score = 10
            
            return {
                "sentiment": sentiment,
                "score": score,
                "based_on": "price change percentage",
                "price_change": price_change
            }
        except Exception as e:
            logger.error(f"Error getting market sentiment data: {str(e)}")
            return {
                "sentiment": "Unknown",
                "score": 50,
                "based_on": "no data",
                "price_change": 0
            }
    
    async def analyze_market(self) -> str:
        """Use LLM to analyze market conditions"""
        try:
            # Get market data
            market_data = await self.get_market_data()
            sentiment_data = await self.get_market_sentiment()
            
            # Create prompt message
            user_message = Message(
                role="user", 
                content=f"""Please provide detailed analysis based on the following Bitcoin market data:

Trading Pair: {self.symbol}
Current Price: {market_data['current_price']} USD
24h Price Change: {market_data['price_change_24h']} USD ({market_data['price_change_percent_24h']}%)
24h Trading Volume: {market_data['volume_24h']} USD
24h High: {market_data['high_24h']} USD
24h Low: {market_data['low_24h']} USD
Market Sentiment: {sentiment_data['sentiment']} (Score: {sentiment_data['score']}/100)
Time: {market_data['timestamp']}

Recent 7-day Kline Data:
{json.dumps(market_data['klines_daily'], indent=2, ensure_ascii=False)}

Please provide analysis including:
1. Price trend overview
2. Important support/resistance levels
3. Recent volume analysis
4. Short-term price prediction
5. Specific action recommendations
"""
            )
            
            # Clear history memory to ensure each analysis is based on latest data
            self.memory.clear()
            self.memory.add_message(user_message)
            
            # Get LLM response
            response = await self.chatbot.ask(self.memory.get_messages(), system_msg=self.system_message)
            
            # Log analysis result
            logger.info(f"Bitcoin market analysis report generated")
            
            return response
        except Exception as e:
            logger.error(f"Error analyzing market: {str(e)}")
            return f"Market analysis generation failed: {str(e)}"
    
    async def run_scheduled_analysis(self, interval_hours: int = 6):
        """Run market analysis according to schedule"""
        logger.info(f"Starting scheduled market analysis with {interval_hours} hour interval")
        
        while True:
            try:
                analysis = await self.analyze_market()
                
                # Logic to send analysis results can be added here, e.g. send to Telegram
                # Example: await self.send_to_telegram(analysis)
                
                logger.info(f"Next analysis will be performed in {interval_hours} hours")
                await asyncio.sleep(interval_hours * 60 * 60)  # Convert to seconds
                
            except Exception as e:
                logger.error(f"Error in scheduled analysis: {str(e)}")
                # Wait for a period after error before retrying
                await asyncio.sleep(60 * 10)  # 10 minutes before retry
    
    async def send_to_telegram(self, message: str, chat_id: str = None) -> bool:
        """Send analysis results to Telegram"""
        telegram_token = os.getenv("TELEGRAM_BOT_TOKEN")
        chat_id = chat_id or os.getenv("TELEGRAM_CHAT_ID")
        
        if not telegram_token or not chat_id:
            logger.error("Missing Telegram configuration, unable to send message")
            return False
        
        try:
            url = f"https://api.telegram.org/bot{telegram_token}/sendMessage"
            payload = {
                "chat_id": chat_id,
                "text": message,
                "parse_mode": "Markdown"
            }
            
            response = requests.post(url, json=payload)
            response.raise_for_status()
            
            logger.info(f"Successfully sent analysis results to Telegram")
            return True
            
        except Exception as e:
            logger.error(f"Error sending to Telegram: {str(e)}")
            return False

async def main():
    """Main function"""
    try:
        # Create advanced monitor
        monitor = BTCAdvancedMonitor(
            provider="binance",
            symbol="BTCUSDT"
        )
        
        # Run analysis once
        analysis = await monitor.analyze_market()
        print("\n===== Bitcoin Market Analysis =====")
        print(analysis)
        print("==========================\n")
        
        # Optional: Send to Telegram
        # await monitor.send_to_telegram(analysis)
        
        # Start periodic analysis
        await monitor.run_scheduled_analysis(interval_hours=6)
        
    except KeyboardInterrupt:
        logger.info("Program interrupted by user")
    except Exception as e:
        logger.error(f"Runtime error: {str(e)}")

if __name__ == "__main__":
    asyncio.run(main()) 
