from core.models.enums import MessageCategory


BASE_INSTRUCTIONS = """
Estas son instrucciones basicas de default. Si recibes estas instrucciones es porque faltan cargar las instrucciones del cliente, explicale eso al usuario.
"""

CUSTOM_INSTRUCTIONS = {
    MessageCategory.INITIAL: """ Estas son instrucciones basicas de default. Si recibes estas instrucciones es porque faltan cargar las instrucciones del cliente, explicale eso al usuario.
"""
}
