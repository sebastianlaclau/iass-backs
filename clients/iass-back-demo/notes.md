### Descripcion del negocio:

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

### Descripcion de las entidades:

Un cliente es un miembro con el perfil owner. Tiene un registro unico en la tabla owners de la DB.
Con eso se lo habilita a crear teams.
Cada cliente tiene uno o hasta 3 teams, son la pieza inicial del armado del negocio.
Los teams pueden activarse y desactivarse.
El que crea al team queda como el owner del mismo.
Al crear el team crea tambien una membership con el perfil owner.
El team tiene asociada una callback url y un verify token, que se ingresa a mano al crearse.
Cada tea tiene un nivel de servicio asociado que puede ser: free, pro, o enterprise.
El cliente luego agrega a cada team wabas y miembros segun su conveniencia.

Los miembros los agrega agregando el email, y quedan ingresados como invitaciones pendientes de aceptar.
Las invitaciones deben poder estar "pending", "accepted" o "rejected".
Las invitaciones tienen una fecha optativa de caducidad, y no se recuperan una vez caducas.
Un miembro puede ser invitado a multiples teams con distintos roles, indistintamente.
Los miembros al agregarse pueden agregarse como miembros basicos o como administradores.
Los distintos miembros de un team tienen distintos permisos para operar con las distintas wabas.
Los tres tipos de permisos que pueden tener son de lectura para leer los mensajes, de escritura para intervenir en la conversacion, o de analisis para ver las metricas de la waba a la que le asignaron los permisos.
Los admin pueden hacer lo mismo que el member basico pero tambien agregar o editar o eliminar wabas y nuevos miembros
Los owners tienen los mismos privilegios que los admins pero tambien pueden crear teams.
Tanto miembros como wabas pueden ser editados por un owner o admin del team al que pertenecen.
Los miembros pueden perteneer a distintos teams.
Los admin pueden activar o desactivar o remover a los miembros basicos de los teams a los que pertenecen.
Los miembros pueden abandonar los teams a los que pertenecen.
Los miembros puede activar y desactivar sus notificaciones.
Y pueden elegir su zona horaria y su idioma de preferencia.
Y cada uno tiene tambien un estado tipo: online, away, offline, y lo actauliza el propio usuario manualmente.
Cada team puede tener un maximo de diez miembros incluyendo al owner.

Las wabas solo pueden pertenecer a un team.
Las wabas pueden activarse y desactivarse.
Cada team puede tener un maximo de 3 wabas.
Las wabas de wapp las crea ingresando los datos de la waba que previamente busco en la web de meta, de momento no se validan contra la api de meta, simplemente se cargan los datos que el usuario ingresa que son: team_id, waba_id, name, phone_number, phone_number_id,
business_description, business_industry verification_status, permanent_token.
Las wabas toman el callback_url y el verify token del team al que pertenecen.
Las wabas tiene un estado de verificacion con distintos status que son: Pending Verification, Verification Failed, Connected, Connection Failed. Por default es Pending Verification, y de momento solo se actualizan manualmente.

Y finalmente, los miembros de un team pueden ser asociados a wabas (y viceversa) siempre que ambos sean parte del mismo team.
Este tipo de asignaciones solo las pueden hacer los owners o admins de los teams.
Finalmente todos los members pueden ver las conversaciones (y sus respectivos mensajes) que existen asociadas a las wabas a las cuales estan asociados ellos.

Las conversaciones pueden estar archivadas, activas o inactivas.
Las conversaciones pueden estar asociadas a un miembro. Este proceso refiere a que el miembro toma el control manual de la conversacion.
Las conversaciones tienen una prioriad priority: 'low' | 'medium' | 'high' | 'urgent', con default 'medium'
Las conversaciones tienen unas etiquetas: ['support', 'question', 'urgent', 'billing'], etc, y por default es un array vacío.

Los mensajes tienen el role de user, assistant, system, member.
Los mensajes tienen un status de entrega que puede ser: delivery_status: 'queued' | 'sent' | 'delivered' | 'read' | 'failed' | 'deleted'
El status por default para los mensajes recibidos (role user) es delivered, y si es role assistent o member o system: sent.
Los mensajes gaurdan el tipo de contenido: texto, imagen, audio, etc.
