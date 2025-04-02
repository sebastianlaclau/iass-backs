# Descripción del Proyecto IAssistance Backends

# Visión General

IAssistance Backends es una plataforma de chatbots inteligentes basada en WhatsApp Business API que permite a empresas automatizar comunicaciones con sus clientes. El sistema procesa mensajes entrantes, los analiza con inteligencia artificial (LLMs), y genera respuestas personalizadas según el contexto específico de cada cliente.

# Arquitectura

# Enfoque Multi-cliente

Monorepo: Todo el código compartido y específico por cliente está en un único repositorio
Multi-instancia: Cada cliente tiene su propia aplicación FastAPI que comparte código base común
Ruta específica por cliente: Cada cliente tiene su propio prefijo de ruta (ej: /api/v1/demo/)

# Estructura pensada inicialmente de Directorios

├── core/ # Código base compartido
│ ├── api/ # Endpoints comunes
│ ├── models/ # Definiciones de datos
│ ├── services/ # Servicios compartidos
│ ├── utils/ # Utilidades compartidas
│ ├── webhooks/ # Manejadores de webhooks
│ ├── storage/ # Persistencia de datos
│ ├── main.py # Fábrica de aplicaciones
│ └── config.py # Configuración base
└── clients/ # Código específico por cliente
├── iass-back-demo/
│ ├── api/ # Endpoints específicos
│ ├── config.py # Configuración específica
│ ├── main.py # Punto de entrada
│ └── .env # Variables de entorno
└── iass-back-emprendemy/
└── ... # Similar estructura

# Patrones de Diseño

Factory Pattern: Para crear instancias de aplicaciones y servicios específicos por cliente
Dependency Injection: Contenedor de servicios que proporciona acceso a recursos compartidos
Service Container: Encapsula dependencias para evitar variables globales
Repository Pattern: Abstracción para acceso a datos (Supabase)
Buffer-Processing Pattern: Sistema de colas para mensajes entrantes

# Tecnologías y Herramientas

Backend: FastAPI + Uvicorn/Gunicorn
Base de Datos: Supabase (PostgreSQL)
IA/LLM: OpenAI GPT-4o (y otros modelos)
Mensajería: WhatsApp Business API
Vectores: Pinecone para búsqueda semántica
Despliegue: Heroku
Notificaciones: SMTP Email (Gmail)

# Clientes Actuales

## Demo Client

Descripción: Cliente demostrativo para probar funcionalidades
Características:
Instrucciones clasificadas (CLASSIFIED strategy): clents/iass-back-demo/prompts.py
Herramientas definidas: clents/iass-back-demo/tools_definition.py

## Emprendemy Client

Descripción: Cliente de emprendimientos educativos
Características:
Instrucciones simples (SINGLE strategy): clents/iass-back-emprendemy/prompts.py
Herramientas definidas: clents/iass-back-emprendemy/tools_definition.py
Configuración de correo específica

# Configuración de Clientes

Cada cliente requiere:

## WABAConfig: Configuración de WhatsApp Business Account

Credenciales de WhatsApp Business API
Configuración de modelo OpenAI
Estrategia de instrucciones
Herramientas disponibles
Configuración SMTP

## <Client>ClientSettings: Configuración específica por cliente

Variables de entorno específicas
Tokens de verificación
Configuración de API

# Flujo de Datos Principal

Meta Webhook envía notificación cuando llega un mensaje a WhatsApp
webhook.py recibe y valida el payload
message_handlers.py procesa y categoriza el mensaje
El mensaje se almacena en buffer y contexto de conversación
openai_handler.py obtiene la respuesta del LLM con las instrucciones adecuadas
La respuesta se envía de vuelta al usuario vía WhatsApp API

# Características Clave

Contexto de Conversación: Mantiene historial para respuestas coherentes
Categorización de Mensajes: Analiza el tipo de consulta para aplicar instrucciones específicas
Caché de Configuración: Almacena configuraciones para optimizar rendimiento
Instrucciones Dinámicas: Adapta el comportamiento del LLM según el contexto
Herramientas Personalizables: Cada cliente puede tener funciones específicas (tools)
Manejo de Concurrencia: Diseño thread-safe para múltiples conversaciones simultáneas

# Consideraciones Técnicas

Escalabilidad: Diseñado para manejar múltiples clientes y WABAs
Concurrencia: Gestión de múltiples conversaciones simultáneas
Stateless: Servicios diseñados para ser sin estado cuando es posible
Fallbacks: Mecanismos para manejar errores en diferentes niveles
Monitoreo: Logging estructurado para seguimiento de actividad
Seguridad: Validación de webhooks y tokens específicos por cliente
