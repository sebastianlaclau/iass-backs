from typing import Any, Dict, List


DEMO_RUN_TOOLS_DEFINITION_EMPRENDEMY: List[Dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "get_course_details",
            "description": "Obtiene información sobre un curso específico. Use 'general' para información general. Use 'specific' SOLO para campos predefinidos: preview_rul, instructor, requirements, duration. Use 'semantic' para preguntas sobre temas o contenido específico",
            "parameters": {
                "type": "object",
                "properties": {
                    "course_id": {
                        "type": "string",
                        "description": "ID del curso",
                        "enum": [
                            "tiktok-reels",
                            "discapacidad",
                            "community-manager",
                            "costura",
                            "babysitter",
                            "bicicletas",
                            "mercadolibre",
                            "peluqueria",
                            "peluqueria-canina",
                        ],
                    },
                    "info_type": {
                        "type": "string",
                        "enum": ["general", "specific", "semantic"],
                        "description": "Tipo de información requerida las tres opciones representan: 1 - general: datos sobre de que trata el curso o en que consiste o un resumen, 2 - specific: para datos de campos especificos definidos, 3 - semantic: para buscar algun dato puntual en el detalle del curso",
                    },
                    "specific_info": {
                        "type": "array",
                        "items": {
                            "type": "string",
                            "enum": [
                                "preview_url",
                                "duration",
                                "instructor",
                                "requirements",
                                # "objectives",
                                # "units",
                                # "description",
                                # "otro",
                            ],
                        },
                        "description": "Lista de información específica requerida cuando info_type es 'specific'",
                    },
                    "query": {
                        "type": "string",
                        "description": "Consulta para búsqueda semántica",
                    },
                    "country_code": {
                        "type": "string",
                        "description": "Código del país",
                        "enum": [
                            "AR",
                            "CO",
                            "MX",
                            "UY",
                            "CL",
                            "CR",
                            "PY",
                            "PE",
                            "OTHER",
                        ],
                    },
                },
                "required": ["course_id", "info_type", "country_code"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_course_price",
            "description": "Obtiene información de precios para un curso en un país específico",
            "parameters": {
                "type": "object",
                "properties": {
                    "country_code": {
                        "type": "string",
                        "description": "Código del país",
                        "enum": [
                            "AR",
                            "CO",
                            "MX",
                            "UY",
                            "CL",
                            "CR",
                            "PY",
                            "PE",
                            "OTHER",
                        ],
                    },
                },
                "required": ["country_code"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "send_sign_up_message",
            "description": "Envía un mensaje al interlocutor con el link para inscribirse en el curso.",
            "parameters": {
                "type": "object",
                "properties": {
                    "course_id": {
                        "type": "string",
                        "description": "ID del curso",
                        "enum": [
                            "tiktok-reels",
                            "bicicletas",
                            "community-manager",
                            "peluqueria",
                            "mercadolibre",
                            "peluqueria-canina",
                            "costura",
                            "babysitter",
                            "discapacidad",
                        ],
                    },
                    "catchy_phrase": {
                        "type": "string",
                        "description": """Frase para agregar al mensaje con el link de inscripcion que incluya estos 3 elementos en orden:
                        1 - Mencione que se le esta compartiendo el link de inscripcion.
                        2 - Invite a inscribirse.
                        3 - Pregunte si hace falta algo mas y se ponga a disposicion""",
                    },
                },
                "required": [
                    "course_id"
                    # "curso",
                    # "url_compra",
                    "catchy_phrase",
                ],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "send_emprendemy_contact",
            "description": "Envía un mensaje con el contacto de WhatsApp de un empleado de Emprendemy que los puede atender personalmente",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "send_conversation_to_supervisor",
            "description": "envia un resumen de la conversacion a un supervisor",
            "parameters": {
                "type": "object",
                "properties": {
                    "notification_type": {
                        "type": "string",
                        "description": "motivo",
                        "enum": [
                            "PRICE_ISSUE",
                            "SPECIAL_REQUEST",
                        ],
                    },
                },
                "required": ["notification_type"],
            },
        },
    },
]
