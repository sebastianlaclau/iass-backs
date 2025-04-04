# core/services/functions_handler.py
import logging
import uuid
from typing import Dict, Any

from core.models.enums import ResponseBehavior
from core.models.responses import FunctionResponse

logger = logging.getLogger(__name__)


class FunctionsHandler:
    """
    Base class for function handlers with core functionality
    """

    def __init__(
        self,
        client_id: str,
        waba_conf,
        sender_phone: str,
        openai_handler,
        message_buffer_manager=None,
        service_container=None,
    ):
        self.waba_conf = waba_conf
        self.sender_phone = sender_phone
        self.openai_handler = openai_handler
        self.conversation_id = openai_handler.conversation_id
        self.client_id = client_id
        self.service_container = service_container or None
        self.message_buffer_manager = message_buffer_manager

        # For backward compatibility
        if self.service_container and not message_buffer_manager:
            self.message_buffer_manager = self.service_container.message_buffer_manager

    async def execute_function(
        self,
        name: str,
        args: Dict[str, Any],
    ) -> FunctionResponse:
        """
        Execute a function by name with the given arguments

        Base implementation returns function not found response
        Override this method in client-specific implementations
        """
        logger.warning(f"Unknown function called: {name}")
        return FunctionResponse(
            success=False,
            data={},
            error=f"Unknown function: {name}",
            response_behavior=ResponseBehavior.NO_FOLLOW_UP,
        )

    async def save_function_execution_message(
        self, function_name: str, args: Dict[str, Any]
    ) -> None:
        """Save function execution log to database"""
        try:
            args_msg = "\n".join(f" - {k}: {v}" for k, v in args.items())
            message_body = f"Function executed: {function_name}\n{args_msg}"

            if self.service_container and hasattr(self.service_container, "db"):
                db = self.service_container.db
                db.save_message(
                    conversation_id=self.conversation_id,
                    message_data={
                        "message": {
                            "id": str(uuid.uuid4()),
                            "text": {"body": message_body},
                        },
                        "type": "system",
                        "is_response": True,
                    },
                )
            else:
                logger.warning(
                    "Could not save function execution message: no database available"
                )
        except Exception as e:
            logger.error(f"Error saving function execution message: {str(e)}")
