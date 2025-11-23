# execution_tracer.py
from spoon_ai.agents.base import BaseAgent
from functools import wraps
import inspect
import logging
logger = logging.getLogger(__name__)

def trace_execution(func):
    """Decorator to trace function execution"""
    @wraps(func)
    async def wrapper(self, *args, **kwargs):
        func_name = func.__name__
        
        # Log function entry
        logger.debug(
            "Function entry",
            function=func_name,
            args=args,
            kwargs=kwargs,
            agent=getattr(self, 'name', 'unknown')
        )
        
        try:
            # Execute function
            result = await func(self, *args, **kwargs)
            
            # Log successful completion
            logger.debug(
                "Function success",
                function=func_name,
                result_type=type(result).__name__,
                agent=getattr(self, 'name', 'unknown')
            )
            
            return result
            
        except Exception as e:
            # Log error
            logger.error(
                "Function error",
                function=func_name,
                error_type=type(e).__name__,
                error_message=str(e),
                agent=getattr(self, 'name', 'unknown')
            )
            raise
    
    return wrapper

#class TracedAgent(BaseAgent):
#    """Agent with method tracing"""
#    
#    @trace_execution
#    async def run(self, message: str, **kwargs):
#        return await super().run(message, **kwargs)
#    
#    @trace_execution
#    async def chat(self, messages, **kwargs):
#        return await super().chat(messages, **kwargs)

