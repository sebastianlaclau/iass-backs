import logging
from typing import Dict, Any

from core.services.functions_handler import FunctionsHandler as BaseFunctionsHandler
from core.models.responses import FunctionResponse
from core.models.enums import ResponseBehavior

logger = logging.getLogger(__name__)


class FunctionsHandler(BaseFunctionsHandler):
    """
    Simple functions handler for demo client
    """

    async def execute_function(
        self,
        name: str,
        args: Dict[str, Any],
    ) -> FunctionResponse:
        """
        Demo client doesn't implement any custom functions
        Just logs the function call and returns a default response
        """
        logger.info(f"Demo client function called: {name} with args: {args}")

        await self.save_function_execution_message(name, args)

        return FunctionResponse(
            success=True,
            data={"message": "Function execution simulated in demo client"},
            follow_up_instructions="This is a demo client without actual function implementations",
            response_behavior=ResponseBehavior.NO_FOLLOW_UP,
        )
