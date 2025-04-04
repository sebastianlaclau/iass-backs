# clients/iass_back_emprendemy/constants.py

from core.models.course import PriceInfo

EMPRENDEMY_CONTACT_INFO = {
    "name": {
        "formatted_name": "Academia Emprendemy",  # Required
        "first_name": "Academia",
        "last_name": "Emprendemy",
    },
    "phones": [
        {
            "phone": "+541156106681",  # Your support phone number
            # "phone": "+54 9 11 4056-2860",  # Your support phone number
            "type": "WORK",
            # "wa_id": "5491140562860",
            "wa_id": "5491156106681",
        }
    ],
    # You can add more fields as needed, such as:
    "emails": [{"email": "support@emprendemy.com", "type": "WORK"}],
    "org": {"department": "Emprendemy"},
}

PRICES_DATA = {
    "AR": PriceInfo(
        price=72000,
        final_price=32400,
        currency="pesos argentinos",
        symbol="$",
        country_code="AR",
    ),
    "CO": PriceInfo(
        price=367650,
        final_price=165400,
        currency="pesos colombianos",
        symbol="$",
        country_code="CO",
    ),
    "MX": PriceInfo(
        price=1880,
        final_price=846,
        currency="pesos mexicanos",
        symbol="$",
        country_code="MX",
    ),
    "UY": PriceInfo(
        price=3000,
        final_price=1350,
        currency="pesos uruguayos",
        symbol="$",
        country_code="UY",
    ),
    "CL": PriceInfo(
        price=64480,
        final_price=29015,
        currency="pesos chilenos",
        symbol="$",
        country_code="CL",
    ),
    "CR": PriceInfo(
        price=53600,
        final_price=24120,
        currency="colones",
        symbol="₡",
        country_code="CR",
    ),
    "PY": PriceInfo(
        price=548000,
        final_price=246600,
        currency="guaraníes",
        symbol="₲",
        country_code="PY",
    ),
    "PE": PriceInfo(
        price=320, final_price=144, currency="soles", symbol="S/", country_code="PE"
    ),
    "OTHER": PriceInfo(
        price=80,
        final_price=36,
        currency="dólares estadounidenses",
        symbol="USD",
        country_code="OTHER",
    ),
}

COURSES_INFO = {
    "tiktok-reels": {
        "id": "tiktok-reels",
        "name": "Crea contenidos efectivos para TikTok & Instagram Reels",
        "url": "https://emprendemy.com/curso/crea-contenidos-para-tiktok-y-reels/",
    },
    "bicicletas": {
        "id": "bicicletas",
        "name": "Mecánica y reparación de bicicletas",
        "url": "https://emprendemy.com/curso/curso-mecanica-reparacion-bicicletas/",
    },
    "community-manager": {
        "id": "community-manager",
        "name": "Community Manager: lidera las Redes Sociales",
        "url": "https://emprendemy.com/curso/curso-community-manager/",
    },
    "peluqueria": {
        "id": "peluqueria",
        "name": "Peluquería Nivel Inicial",
        "url": "https://emprendemy.com/curso/curso-de-peluqueria-inicial/",
    },
    "mercadolibre": {
        "id": "mercadolibre",
        "name": "Multiplica tus Ventas en Mercado Libre",
        "url": "https://emprendemy.com/curso/curso-ventas-en-mercado-libre/",
    },
    "peluqueria-canina": {
        "id": "peluqueria-canina",
        "name": "Peluquería Canina | Nivel inicial",
        "url": "https://emprendemy.com/curso/curso-de-peluqueria-canina/",
    },
    "costura": {
        "id": "costura",
        "name": "Costura Responsable y Reciclaje de Prendas",
        "url": "https://emprendemy.com/curso/curso-costura-responsable-y-reciclaje-de-prendas/",
    },
    "babysitter": {
        "id": "babysitter",
        "name": "Cuidado de niños y niñas: Babysitter profesional",
        "url": "https://emprendemy.com/curso/cuidado-de-ninos-babysitter/",
    },
    "discapacidad": {
        "id": "discapacidad",
        "name": "Acompañamiento de personas con discapacidad",
        "url": "https://emprendemy.com/curso/curso-acompanante-personas-discapacidad/",
    },
}

SUPERVISOR_NOTIFICATION_TYPE = {
    "PRICE_ISSUE": {
        "prefix": "⚠️ ASUNTO EN PRECIOS/DESCUENTOS",
        "can_notify_user": True,
        "subject_prefix": "🏷️ Consulta de Precios",
        "history_message": "la consulta de precios/descuentos",
    },
    "SPECIAL_REQUEST": {
        "prefix": "🔔 SUGERENCIA/RECLAMO",
        "can_notify_user": True,
        "subject_prefix": "💡 Sugerencia/Reclamo",
        "history_message": "el pedido especial/sugerencia",
    },
}
