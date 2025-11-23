# Name:        Agentic AI LLM Classify Sentiment Analysis Tool
# Description: Provide Sentiment Analysis based on summaries of the most 5 recent news articles about the entity.
#
# Author:      Victor Tong
# Websites:    cryptozk.com, wordpy.com, angel.webplus.com, webplusshop.com,
#              stockinfo.us/stock/chart/livestock, gogame.com/shop
# Sponsored by:  AIGlobalCampus.com
# Created:     2025-11-23 Done overnight, 5 hours late start at
#              Scoop AI Hackathon, Santa Clara, CA, USA
# Copyright:   (c) Victor Tong 2025
# Licence:     Whatever license of spoon_ai
#
from exec_tracer import trace_execution  # couldn't get tracing to work
from spoon_ai.agents.toolcall import ToolCallAgent
from spoon_ai.tools import ToolManager
from spoon_ai.tools.base import BaseTool
from spoon_ai.chat import ChatBot
from spoon_ai.schema import Message
from pydantic import Field
from dotenv import load_dotenv
import aiohttp, asyncio, logging, os

chatbot=ChatBot(
    llm_provider="openai",
    model_name="gpt-4.1"
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
load_dotenv(override=True)

WebplusSearchUrl = 'https://cryptozk.com/api/search/PjL/?page={}&per_page={}&highlight=false&site_id=7200&q={}&lang={}&access_code=82903921819870'
page, per_page, lang, access_code = 1, 5, 'en', 82902894822823

ClassifyPrompt = "Classify entity '{}' in text into neutral, negative, or positive sentiment.\nText: {}.\n Sentiment:\n"



class ClassifySentimentTool(BaseTool):
    '''
    Ask: recent sentiment about Nvidia? 
    📋 Answer: The sentiment result for Nvidia is neutral, with recent news providing a balanced mix of factual updates, product enhancements, and some criticism, but no strong positive or negative tone.
    Authors comment:  Nvidia had fallen after blowout earnings report. If we include 500 past news articles, Nvidia will be positive or bullish!

    Ask: recent sentiment about Nuclear Power?
    📋 Answer: The previous result provides a clear and complete summary of recent sentiment about Nuclear Power: it is positive, with news highlighting increased investments, long-term deals, economic viability, safety, and its role in meeting energy demands. There are no negative or neutral statements reported.
    '''
    name: str = "entity_sentiment"
    description: str = "Get sentiment for an entity from recent news."
    parameters: dict = {
        "type": "object",
        "properties": {
            "entity": {
                "type": "string",
                "description": "Entity's name such as a person's name, "
                    "company, stock, or crypto name or ticker symbol. "
                    "e.g.: 'Tesla', 'Bitcoin', 'ETH', 'Nuclear Power'."
            }
        },
        "required": ["entity"]
    }

    async def execute(self, entity: str,
                      url: str = None, method: str = "GET",
                      headers: dict = None
                      ) -> str:
        SearchUrl = WebplusSearchUrl.format(page, per_page, entity, lang,
                                            access_code)
        url = url or os.getenv("WEBPLUS_SEARCH_URL") or SearchUrl
        print(f"VT1 execute entity={entity}, {url}")

        # Framework provides automatic error handling and retry logic
        async with aiohttp.ClientSession() as session:
            #async with session.get(url) as resp:
            async with session.request(method, url, headers=headers
                                       ) as resp:
                if resp.status != 200:
                    return f"Failed to obtain news text, status code:{resp.status}"
                JsonD = await resp.json()
                sentiment = await classify_sent(JsonD, entity)

                #if self.config["memory"]["enabled"]:
                #    self.store_conversation(message, response)
                return (sentiment, )
                #return dict(  # return ToolResult(
                #    output=sentiment,
                #    system=f"API call successful: {resp.status}"
                #)


class SentimentAgent(ToolCallAgent):
    """
    An intelligent assistant capable of performing useful sentiment analysis.
    """
    name: str = "sentiment_agent"
    description: str = (
        "A smart assistant that can:\n"

        "1. Provide sentiment for a given entity such as person, company, crypto, ticker, etc.\n"
    )

    system_prompt: str = """
    You are a helpful assistant with access to tools. You can:

    1. Get the sentiment of a specific entity, e.g.: 'Tesla', 'Bitcoin', 'ETH' from recent news stories.

    For each user question, decide whether to invoke a tool or answer directly.
    If a tool's result isn't sufficient, analyze the result and guide the next steps clearly.
    """

    next_step_prompt: str = (
        "Based on the previous result, decide what to do next. "
        "If the result is incomplete, consider using another tool or asking for clarification."
    )

    max_steps: int = 5

    available_tools: ToolManager = Field(default_factory=lambda: ToolManager([
        ClassifySentimentTool(),  # SmartWeatherTool(),
    ]))

    @trace_execution  # couldn't get tracing to work
    async def run(self, message: str, **kwargs):
        return await super().run(message, **kwargs)
    
    @trace_execution  # couldn't get tracing to work
    async def chat(self, messages, **kwargs):
        return await super().chat(messages, **kwargs)



async def classify_sent(JsonD, entity) -> str:
    """Use LLM to classify entity sentiment"""
    PostDL = JsonD['items']
    text = '\n'.join([PostD['sum_nlp'] for PostD in PostDL])
    message = ClassifyPrompt.format(entity, text)
    messages = [Message(role="user", content=message)]
    resp = await chatbot.ask_tool(messages, tool_choice=None)
    return resp


async def main():
    print("=== Using SentimentAgent with New LLM Architecture ===")
    sent_agent = SentimentAgent(
        llm=chatbot
    )
    print("✓ Using LLM manager architecture")
    sent_agent.clear() # Reset Agent state
    print("\n🤖 Agent is preparing ...")

    while True:
        user_input = input("You:  "
            "[hint: recent sentiment about Bitcoin? (or Nuclear Power)]\n")
        if user_input.lower() in ['quit', 'exit', 'bye']:
            break

        resp = await sent_agent.run(user_input)
        print(f"\n📋 Answer: {resp}\n")

        # Show agent statistics if using new architecture
        if hasattr(sent_agent.llm, 'use_llm_manager') and \
                   sent_agent.llm.use_llm_manager:
            try:
                from spoon_ai.llm.manager import get_llm_manager
                manager = get_llm_manager()
                stats = manager.get_stats()
                print("📊 LLM Manager Statistics:")
                print("  - Default provider: ",
                      stats['manager']['default_provider'])
                print("  - Fallback chain: ",
                      stats['manager']['fallback_chain'])
                print("  - Load balancing: ",
                      stats['manager']['load_balancing_enabled'])
            except Exception as e:
                print(f"⚠ Could not retrieve statistics: {e}")


if __name__ == "__main__":
    asyncio.run(main())


#export DEBUG=true       # couldn't get debug to work
#export LOG_LEVEL=debug  # couldn't get debug to work
# python angent5.py
