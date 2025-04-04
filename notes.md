# TODO EMPRENDEMY

- no se a cual es la url a la que esta apuntando la app del chino porque no me la deja ver.
- cuando este actualizado heroku hay que ponerle la nueva url y hacer los ajustes en los settings del cliente en el repo para que use los valores de la app del chino, o mantener el uso de la app de iassistance y que el chino use el numero de telefono mio.

# TODO GENERAL

- cuando este mas o menos funcionando localmente empujar y reemplazar la app en heroku conectando con github.

<!--
Tengo un backend que es un servicio que recibe mensajes de whatsapp y los procesa, en heroku.
Guarda mensajes y conversaciones en Supabase, el proyecto esta creado con el starter de supabase autentication y nextjs asi que estan todos los files necesarios para eso.
Un frontend en nextjs con tw y shadcn, un theme light and dark, donde mis clientes se dan de alta con la autenticacion de supabase.
Tengo hooks, algo de context y SWR.
En el frontend se ven los mensajes procesados y se configuran los equipos
Desde ahi previamente me tienen que validar en facebook y dar permisos para crearles una app, una waba, un catalogo o permitirme asociar otros previamente previamente creados a su cuenta.
Al hacerlo yo le editaria el campo callback url para que meta envie los webhooks a la direccion que yo le pase.
El ciente crea un team, agrega emails de miembros, agrega wabas de meta para gestionar. define cuales miembros manejan cuales wabas, cuales permisos les da para cada waba (assignments) y en funcion de ello se le asignan los mensajes entrantes.
 -->

# Descripción del Proyecto IAssistance Backends

# Visión General

IAssistance Backends es una plataforma de chatbots inteligentes basada en WhatsApp Business API que permite a empresas automatizar comunicaciones con sus clientes. El sistema procesa mensajes entrantes, los analiza con inteligencia artificial (LLMs), y genera respuestas personalizadas según el contexto específico de cada cliente.

# Arquitectura

# Enfoque Multi-cliente

Monorepo: Todo el código compartido y específico por cliente está en un único repositorio
Aplicación centralizada: Una única aplicación FastAPI que monta las aplicaciones de cliente como submódulos
Único punto de entrada para webhooks: Un solo endpoint recibe webhooks de WhatsApp y los enruta al cliente correspondiente
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
└── iass_back_emprendemy/
└── ... # Similar estructura

# Patrones de Diseño

Factory Pattern con caché: Para crear y reutilizar instancias de aplicaciones de cliente de forma eficiente
Mount Points: Montaje de aplicaciones de cliente bajo una aplicación principal centralizada
Dependency Injection: Contenedor de servicios que proporciona acceso a recursos compartidos
Service Container: Encapsula dependencias para evitar variables globales
Repository Pattern: Abstracción para acceso a datos (Supabase)
Buffer-Processing Pattern: Sistema de colas para mensajes entrantes
Router Pattern: Identificación y enrutamiento dinámico de webhooks al cliente correspondiente

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
Instrucciones simples (SINGLE strategy): clents/iass_back_emprendemy/prompts.py
Herramientas definidas: clents/iass_back_emprendemy/tools_definition.py
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

Meta Webhook envía notificación a un único endpoint centralizado cuando llega un mensaje a cualquier WhatsApp
El endpoint centralizado en webhook.py recibe, valida el payload e identifica a qué cliente pertenece (basado en WABA ID o Phone ID)
El mensaje se enruta al procesador específico del cliente correspondiente
message_handlers.py procesa y categoriza el mensaje según el contexto y configuración del cliente
El mensaje se almacena en buffer y contexto de conversación específico del cliente
openai_handler.py obtiene la respuesta del LLM con las instrucciones adecuadas para ese cliente
La respuesta se envía de vuelta al usuario vía WhatsApp API usando las credenciales del cliente correspondiente

# Características Clave

Contexto de Conversación: Mantiene historial para respuestas coherentes
Categorización de Mensajes: Analiza el tipo de consulta para aplicar instrucciones específicas
Caché de Configuración: Almacena configuraciones para optimizar rendimiento
Instrucciones Dinámicas: Adapta el comportamiento del LLM según el contexto
Herramientas Personalizables: Cada cliente puede tener funciones específicas (tools)
Manejo de Concurrencia: Diseño thread-safe para múltiples conversaciones simultáneas

# Consideraciones Técnicas

Escalabilidad: Diseñado para manejar múltiples clientes y WABAs bajo una única infraestructura centralizada
Despliegue simplificado: Una sola aplicación para desplegar en Heroku, reduciendo costos y complejidad operativa
Concurrencia: Gestión eficiente de múltiples conversaciones simultáneas con procesamiento en segundo plano
Stateless: Servicios diseñados para ser sin estado cuando es posible, facilitando la escalabilidad horizontal
Fallbacks: Mecanismos para manejar errores en diferentes niveles, con aislamiento entre clientes
Monitoreo: Logging estructurado para seguimiento de actividad con identificación de cliente
Seguridad: Validación centralizada de webhooks con tokens específicos por cliente
Tolerancia a fallos: El fallo en un cliente no afecta a los demás gracias a la arquitectura modular
