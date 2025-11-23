#!/usr/bin/env python
# btc_price_agent/btc_price_monitor.py

import os
import sys
import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

# Add parent directory to path to ensure spoon_ai package can be imported
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

# Import SpoonAI components
from spoon_ai.chat import ChatBot, Memory
from spoon_ai.schema import Message
from spoon_ai.monitoring.core.tasks import MonitoringTaskManager
from spoon_ai.monitoring.core.alerts import Metric, Comparator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()]
)

logger = logging.getLogger("btc-price-agent")

class BTCPriceAgent:
    """Bitcoin Price Monitoring Agent"""
    
    def __init__(
        self,
        llm_provider: str = "anthropic",
        model_name: str = "claude-3-7-sonnet-20250219",
        notification_channels: List[str] = ["telegram"],
        check_interval_minutes: int = 5,
    ):
        # Initialize monitoring task manager
        self.task_manager = MonitoringTaskManager()
        
        # Initialize ChatBot
        self.chatbot = ChatBot(
            llm_provider=llm_provider,
            model_name=model_name,
            api_key=os.getenv("ANTHROPIC_API_KEY") if llm_provider == "anthropic" else os.getenv("OPENAI_API_KEY")
        )
        
        # Initialize memory
        self.memory = Memory()
        
        # Save configuration
        self.notification_channels = notification_channels
        self.check_interval_minutes = check_interval_minutes
        
        # System message
        self.system_message = """You are a professional cryptocurrency market analyst, responsible for monitoring Bitcoin price fluctuations and providing analysis.
        When prices trigger thresholds, you need to provide concise price alerts and market analysis.
        The analysis should consider price trends, important support/resistance levels, and recent market sentiment.
        """
        
        logger.info("BTC price monitoring Agent initialized")
    
    def setup_price_monitor(
        self, 
        symbol: str = "BTCUSDT",
        price_threshold: float = None,
        price_change_threshold: float = 5.0,
        market: str = "cex",
        provider: str = "binance",
        expires_in_hours: int = 24,
        notification_params: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Setup price monitoring task"""
        
        # For setting up both price threshold and price change monitoring
        tasks_created = []
        
        # If specific price threshold is set, create price threshold monitoring
        if price_threshold is not None:
            price_monitor_config = {
                "market": market,
                "provider": provider,
                "symbol": symbol,
                "metric": Metric.PRICE.value,
                "threshold": price_threshold,
                "comparator": Comparator.GREATER_THAN.value,  # Comparator can be modified as needed
                "name": f"Bitcoin Price Monitor - {price_threshold} USD",
                "check_interval_minutes": self.check_interval_minutes,
                "expires_in_hours": expires_in_hours,
                "notification_channels": self.notification_channels,
                "notification_params": notification_params or {}
            }
            
            # Create price threshold monitoring task
            price_task = self.task_manager.create_task(price_monitor_config)
            tasks_created.append(price_task)
            logger.info(f"Created price threshold monitoring: {symbol} > {price_threshold}")
        
        # Create price change percentage monitoring
        price_change_config = {
            "market": market,
            "provider": provider,
            "symbol": symbol,
            "metric": Metric.PRICE_CHANGE_PERCENT.value,
            "threshold": price_change_threshold,
            "comparator": Comparator.GREATER_THAN.value if price_change_threshold > 0 else Comparator.LESS_THAN.value,
            "name": f"Bitcoin Price Change Monitor - {price_change_threshold}%",
            "check_interval_minutes": self.check_interval_minutes,
            "expires_in_hours": expires_in_hours,
            "notification_channels": self.notification_channels,
            "notification_params": notification_params or {}
        }
        
        # Create price change monitoring task
        price_change_task = self.task_manager.create_task(price_change_config)
        tasks_created.append(price_change_task)
        logger.info(f"Created price change monitoring: {symbol} change {price_change_threshold}%")
        
        return {
            "tasks_created": tasks_created,
            "task_count": len(tasks_created)
        }
    
    async def process_notification(self, alert_data: Dict[str, Any]) -> str:
        """Process and enhance notification content"""
        # Extract relevant information from alert data
        symbol = alert_data.get("symbol", "BTCUSDT")
        current_value = alert_data.get("current_value", 0)
        threshold = alert_data.get("threshold", 0)
        metric = alert_data.get("metric", "price")
        
        # Create prompt message for LLM
        user_message = Message(
            role="user", 
            content=f"""Bitcoin price monitoring triggered an alert:
            - Trading Pair: {symbol}
            - Current Value: {current_value}
            - Threshold: {threshold}
            - Metric: {metric}
            - Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
            
            Please provide a brief price alert and market analysis, including:
            1. Brief description of price movement
            2. Potential recent support/resistance levels
            3. Brief view on short-term trends
            """
        )
        
        # Add message to memory
        self.memory.add_message(user_message)
        
        # Get LLM response
        response = await self.chatbot.ask(self.memory.get_messages(), system_msg=self.system_message)
        
        # Add assistant response to memory
        assistant_message = Message(role="assistant", content=response)
        self.memory.add_message(assistant_message)
        
        return response
    
    def get_active_tasks(self) -> Dict[str, Any]:
        """Get all active monitoring tasks"""
        return self.task_manager.get_tasks()
    
    def stop_all_tasks(self) -> bool:
        """Stop all monitoring tasks"""
        tasks = self.task_manager.get_tasks()
        success = True
        
        for task_id in tasks:
            if not self.task_manager.delete_task(task_id):
                success = False
                logger.error(f"Unable to delete task: {task_id}")
        
        return success

async def main():
    """Main function, setup and run Bitcoin price monitoring"""
    try:
        # Create Bitcoin price Agent
        btc_agent = BTCPriceAgent(
            notification_channels=["telegram"],
            check_interval_minutes=2
        )
        
        # Setup monitoring parameters
        # These parameters can be adjusted as needed
        notification_params = {
            "telegram": {
                "chat_id": os.getenv("TELEGRAM_CHAT_ID", "")  # Replace with your Telegram chat_id
            }
        }
        
        # Setup price threshold and price change monitoring
        result = btc_agent.setup_price_monitor(
            symbol="BTCUSDT",
            price_threshold=70000,  # Trigger when BTC price exceeds 70000 USD
            price_change_threshold=3.0,  # Trigger when BTC price changes more than 3% within 24 hours
            notification_params=notification_params,
            expires_in_hours=48  # Monitoring lasts for 48 hours
        )
        
        logger.info(f"Created {result['task_count']} monitoring tasks")
        
        # After running for a while, you can call the code below to stop all tasks
        # Here we wait for 3 minutes just for demonstration, in actual use it can be adjusted as needed
        # await asyncio.sleep(180)  # Wait for 3 minutes
        # btc_agent.stop_all_tasks()
        # logger.info("All monitoring tasks stopped")
        
        # Keep main program running
        while True:
            await asyncio.sleep(60)
            logger.info("Monitoring service is running...")
        
    except KeyboardInterrupt:
        logger.info("Program interrupted by user")
    except Exception as e:
        logger.error(f"Runtime error: {str(e)}")

if __name__ == "__main__":
    asyncio.run(main()) 