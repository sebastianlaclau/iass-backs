# core/utils/logging.py
import logging
import textwrap
from typing import Dict, List

logger = logging.getLogger(__name__)


class IndentedFormatter(logging.Formatter):
    def __init__(self, fmt=None, datefmt=None, max_width=100):
        super().__init__(fmt, datefmt)
        self.max_width = max_width
        # Calculamos el tamaño de la indentación basándonos en el formato
        sample_record = logging.LogRecord(
            "name", logging.INFO, "pathname", 1, "msg", (), None
        )
        base_message = super().format(sample_record)
        prefix_length = len(base_message) - len(str(sample_record.msg))
        self.subsequent_indent = " " * prefix_length

    def format(self, record):
        # Obtener el mensaje formateado inicial
        formatted = super().format(record)

        # Separar el prefijo (filename:lineno - levelname - ) del mensaje
        lines = formatted.splitlines()
        if not lines:
            return formatted

        first_line = lines[0]
        # Encontrar la posición donde comienza el mensaje real
        msg_start = first_line.find(" - ", first_line.find(" - ") + 3) + 3

        if msg_start > 0:
            prefix = first_line[:msg_start]
            message = first_line[msg_start:]

            # Aplicar el wrapping al mensaje
            wrapper = textwrap.TextWrapper(
                width=self.max_width,
                initial_indent="",
                subsequent_indent=self.subsequent_indent,
                break_long_words=False,
                break_on_hyphens=False,
            )

            wrapped_message = wrapper.fill(message)
            formatted = prefix + wrapped_message

        return formatted


# def setup_logging():
#     """Configure logging for development environment"""
#     # Formato personalizado
#     log_format = "%(filename)s:%(lineno)d - %(levelname)s - %(message)s"
#     formatter = IndentedFormatter(log_format)

#     # Configurar loggers de la aplicación
#     app_loggers = ["app.api.endpoints.webhook", "app.services.whatsapp"]

#     for logger_name in app_loggers:
#         logger = logging.getLogger(logger_name)
#         logger.handlers = []  # Limpiar handlers existentes
#         handler = logging.StreamHandler()
#         handler.setFormatter(formatter)
#         logger.addHandler(handler)
#         logger.propagate = False
#         logger.setLevel(logging.DEBUG)  # Establecer nivel a DEBUG

#     # Desactivar logs no deseados
#     logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
#     logging.getLogger("httpx").setLevel(logging.WARNING)


def setup_logging():
    """Configure logging for development environment with colored output"""
    import logging
    import sys

    # Define color codes
    COLORS = {
        "DEBUG": "\033[94m",  # Blue
        "INFO": "\033[92m",  # Green
        "WARNING": "\033[93m",  # Yellow
        "ERROR": "\033[91m",  # Red
        "CRITICAL": "\033[91m\033[1m",  # Bold Red
        "RESET": "\033[0m",  # Reset
    }

    class ColoredFormatter(logging.Formatter):
        def format(self, record):
            levelname = record.levelname
            message = super().format(record)
            return f"{COLORS.get(levelname, '')}{message}{COLORS['RESET']}"

    # Custom format that includes level and filename
    log_format = "%(levelname)s: %(message)s (%(filename)s:%(lineno)d)"
    colored_formatter = ColoredFormatter(log_format)

    # Disable propagation for uvicorn loggers to avoid duplicates
    for logger_name in ["uvicorn", "uvicorn.error", "uvicorn.access"]:
        logger = logging.getLogger(logger_name)
        logger.propagate = False

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)

    # Clear existing handlers and add a single console handler
    root_logger.handlers = []
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(colored_formatter)
    root_logger.addHandler(handler)

    # Silence third-party libraries
    third_party_libs = ["httpx", "supabase", "asyncio"]
    for lib in third_party_libs:
        logging.getLogger(lib).setLevel(logging.CRITICAL)

    # para minimizar los logs de openai
    logging.getLogger("openai").setLevel(logging.WARNING)


def log_messages(
    messages: List[Dict[str, str]],
    title: str = None,
    standard_length: int = 1000,
    system_length: int = 1000,
    preview_standard: bool = True,
    preview_system: bool = False,
) -> None:
    if title:
        logger.info(f"{title}:")

    if isinstance(messages, str):
        try:
            messages = eval(messages)  # Temporary fix to parse string back to list
        except:
            logger.error("Could not parse messages string")
            return

    for idx, msg in enumerate(messages):
        content = msg.get("content", "").strip()
        content = ". ".join(
            line.strip() for line in content.splitlines() if line.strip()
        )

        is_system = msg["role"] == "system"
        length = system_length if is_system else standard_length
        use_preview = preview_system if is_system else preview_standard

        if use_preview and len(content) > length:
            content = f"{content[:length]}..."

        logger.info(f"Message {idx + 1} - {msg['role']}: {content}")

        if msg["role"] == "function":
            logger.info(f"  Function: {msg.get('name', 'unknown')}")
