Recomendaciones:
Incluye un README.md en la carpeta iass-backends con instrucciones sobre:
Cómo usar el script de creacion de clientes.
Es algo que vale la pena para ordenar y fundamentalmente si tenes muchso clientes. Pero solo asi. por hora lo hago manual.
La idea es tener un template y un proceso standard que automatice todo: repo online, conexion con el origen, creacion en heroku, seteo de variables de entorno.

### Recomendaría una arquitectura híbrida que combine:

# Núcleo compartido (core library/service):

Infraestructura para webhooks de Meta
Almacenamiento de mensajes/conversaciones

# Módulos específicos por cliente:

Implementados como plugins o módulos configurables
Cada cliente tendría su propio repositorio de configuración
Workflows específicos de procesamiento de mensajes
Lógica de integración con modelos

# Servicios independientes para procesamiento de alta carga:

Un servicio separado para manejar la convergencia y frecuencia de mensajes
Podría escalarse independientemente según necesidades

## Consideraciones y posibles desventajas

-Gestión de múltiples aplicaciones: Tendrás que gestionar múltiples aplicaciones en Heroku, lo que puede ser más complejo administrativamente.
-Actualizaciones del código compartido: Cuando necesites actualizar lógica común, deberás hacerlo en múltiples repositorios o despliegues.
-Costos potencialmente mayores: Heroku cobra por aplicación, así que tener múltiples aplicaciones podría aumentar tus costos, especialmente si no optimizas los planes para cada cliente.
-CI/CD más complejo: Tendrás que establecer pipelines de integración/despliegue continuo para múltiples aplicaciones.

Ventajas de tener servicios separados por cliente en Heroku

Aislamiento completo: Cada cliente opera en un entorno aislado, lo que significa que los problemas de un cliente no afectarán a otros.
Escalabilidad independiente: Puedes escalar cada servicio según las necesidades específicas de cada cliente. Si un cliente tiene un volumen mucho mayor de mensajes, puedes asignarle más recursos sin afectar a los demás.
Configuración simplificada con Meta: Cada cliente simplemente configura su webhook de WhatsApp hacia su URL específica, sin necesidad de parámetros adicionales para identificar al cliente.
Despliegues con menor riesgo: Puedes actualizar el servicio de un cliente sin afectar a los demás, reduciendo el impacto potencial de un despliegue problemático.
Gestión de recursos clara: La facturación y el uso de recursos en Heroku se vuelven transparentes por cliente, facilitando el seguimiento de costos.
Personalización extrema: Puedes modificar significativamente la lógica de procesamiento para un cliente específico sin preocuparte por efectos secundarios en otros.

# Recomendaciones

Sistema de plantillas para nuevos clientes: Mantén un repositorio plantilla que puedas clonar rápidamente para configurar un nuevo cliente.
Herramientas de gestión centralizadas: Desarrolla scripts o herramientas para administrar y actualizar todas tus aplicaciones Heroku desde un lugar centralizado.
Monitoreo unificado: Implementa un sistema de monitoreo que agrupe logs y métricas de todas tus aplicaciones en un solo panel.

## Important Notes

1. Messages can only be sent to numbers that have interacted with your business in the last 24 hours
2. Template quality updates indicate changes in your message template performance
3. The webhook supports both real-time updates and test payloads
4. All webhook calls require proper WhatsApp Business Account configuration

# Consideraciones clave

-Código compartido vs. específico: Mencionas que hay mucho código compartido (autenticación, gestión de equipos) pero también lógica específica por cliente (workflows, respuestas del modelo).
-Frecuencia de mensajes: Necesidad de controlar y minimizar convergencia de mensajes.
-Actualizaciones y mejoras: La mayoría serían específicas por cliente.
-Escalabilidad: Necesidad de escalar diferentes partes del sistema de forma independiente.

# Meta Cloud Message Processing API

This project is a Python API for receiving and processing Meta Cloud messages. It uses OpenAI for processing and sends responses back to a specified number.

## Setup

3. Set up environment variables in a `.env` file
4. Run the server: `uvicorn app.main:app --reload`

## TODOS

En handle_openai_response, aca: if not api_response.tool_calls: try: if api_response.content:....este mensaje no se esta guardando en el historial.
hay veces que cuando llama a una funcion ademas tambien manda un texto, y ahora no lo estamos mandando ese texto, y esta bueno.

# ETAPA DOS.

# TODO: armar un frontend que sea una web, con login para los clientes.

# ETAPA EMPRENDEMY OPERATIVO

# TODO: el formulario de curso, del frontend, deberia tener el campo para la url de inscripcion.

# TODO: el nombre y o ubicacion se tiene que guardar en algun lado ni bien se conoce.

# TODO: chinito el template de la descripcion canchera tendria que empezar con un: "El curso xxxxx consta de...." porque puede que en la conversacion pregunten por dos cursos. Me parece que por el formato del texto, no resta nada.

# TODO: agregar una respuesta para los emojis

# TODO: agregar manejo de alucinaciones en consultas sobre los cursos

# FRONTEND

# TODO: revisar cuales mensajes se guardan en la base y cuales se muestran y como en la vista de los dialogos (distinto de la conversation history)

# TODO: activo y desactivo se deberia marcar por algun color nomas, y que arriba aparezcan las conversas ativas.

# TODO: que los mensajes de sistema solo me los muestre a mi

# BACKEND

# TODO: cuando meto muchos mensajes juntos, en el context no me aparecen en orden: los esta ordenando en el buffer? y en el context?

# TODO: el mecanismo que dispara el procesamiento de los mensajes en el buffer no tendria que estar suelto del mecanismo de inicializacion. mas bien podria ser algo asi como que cuando se inicializa o cuando ingresa, si no esta bloqueado ese buffer se procesa, y si esta bloqueado que genere un trigger que va insistir cada x tiempo y cuando finalmente arranque a procesarse, que lo haga en conjunto con cualquier otro mensaje que pueda haber pendiente en el buffer en ese momento.

# TODO porque la gestion del buffer es asincronica y la del contexto es sincronica

# INFRAESTRUCTURA

# TODO: Tener un mensaje de fallback para el usuario cuando OpenAI no esté disponible

# TODO: agregar dato de tokens a cada conversacion

# TODO: agregar credito a los numeros de telefono.

# TODO: vamos a tener que modificar la DB para meter system tambien.

# TODO: tenemos que meter un mecanismo para que el usuario administrador pueda meter mano en la conversacion

# TODO: tambien tenemos que meter un mecanismo para enviar mensajes para que el usuario informe si el asistente cumplio con lo que necesitaba o no.

# TODO: webhook.py:2448 - ERROR - Error processing buffer 5491135568298_365401589983890: Could not acquire lock for 5491135568298_365401589983890 after 30 seconds

# Traceback (most recent call last):

# File "/home/sebastian/Desktop/programacion/202409 bot-llm-wapp-empre/app/api/endpoints/webhook.py", line 2399, in process_buffered_messages

# async with message_buffer_manager.with_lock(buffer_key):

# File "/home/sebastian/Desktop/programacion/202409 bot-llm-wapp-empre/app/api/endpoints/webhook.py", line 2770, in **aenter**

# raise TimeoutError(

# TimeoutError: Could not acquire lock for 5491135568298_365401589983890 after 30 seconds

# webhook.py:2308 - INFO - Completed message processing for 5491135568298

# webhook.py:2448 - ERROR - Error processing buffer 5491135568298_365401589983890: Could not acquire lock for 5491135568298_365401589983890 after 30 seconds

# Traceback (most recent call last):

# File "/home/sebastian/Desktop/programacion/202409 bot-llm-wapp-empre/app/api/endpoints/webhook.py", line 2399, in process_buffered_messages

# async with message_buffer_manager.with_lock(buffer_key):

# File "/home/sebastian/Desktop/programacion/202409 bot-llm-wapp-empre/app/api/endpoints/webhook.py", line 2770, in **aenter**

# raise TimeoutError(

# TimeoutError: Could not acquire lock for 5491135568298_365401589983890 after 30 seconds

# webhook.py:2308 - INFO - Completed message processing for 5491135568298

# TODO sistema mas robusto de background tasks like reddit o rabbitMQ
