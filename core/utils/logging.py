import logging
import textwrap


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


def setup_logging():
    """Configure logging for development environment"""
    # Formato personalizado
    log_format = "%(filename)s:%(lineno)d - %(levelname)s - %(message)s"
    formatter = IndentedFormatter(log_format)

    # Configurar loggers de la aplicación
    app_loggers = ["app.api.endpoints.webhook", "app.services.whatsapp"]

    for logger_name in app_loggers:
        logger = logging.getLogger(logger_name)
        logger.handlers = []  # Limpiar handlers existentes
        handler = logging.StreamHandler()
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.propagate = False
        logger.setLevel(logging.DEBUG)  # Establecer nivel a DEBUG

    # Desactivar logs no deseados
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
