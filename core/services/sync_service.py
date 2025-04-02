# core/services/sync_service.py
import logging
from datetime import datetime, timezone
from core.config import config_manager

logger = logging.getLogger(__name__)


class SyncService:
    def __init__(self, service_container):
        self.service_container = service_container
        self.supabase = service_container.supabase_client
        # Get project config
        self.project_config = config_manager.get_project_config()

    async def sync_development_conversations(self):
        """
        Sincroniza las conversaciones activas en cache local con la base de datos.
        Solo archiva y recrea conversaciones que tienen mensajes.
        """
        logger.warning("🔄 INICIANDO SINCRONIZACIÓN DE CONVERSACIONES DE DESARROLLO 🔄")

        if not self.project_config.should_sync_conversations:
            logger.warning(
                "❌ Sincronización deshabilitada o no en ambiente de desarrollo"
            )
            return

        try:
            # Obtener TODAS las conversaciones activas de los números habilitados
            enabled_phones = self.project_config.sync_enabled_phones
            if not enabled_phones:
                logger.warning("⚠️ No hay teléfonos habilitados para sincronización")
                return

            logger.warning(f"📱 Procesando teléfonos: {enabled_phones}")

            now = datetime.now(timezone.utc)

            for phone in enabled_phones:
                # Buscar todas las conversaciones activas para este número
                current_convs = (
                    self.supabase.table("conversations")
                    .select("id, waba_id")
                    .eq("phone_number", phone)
                    .eq("status", "active")
                    .execute()
                )

                logger.warning(
                    f"📱 Encontradas {len(current_convs.data)} conversaciones activas para {phone}"
                )

                for conv in current_convs.data:
                    # Verificar si la conversación tiene mensajes
                    messages = (
                        self.supabase.table("messages")
                        .select("id")
                        .eq("conversation_id", conv["id"])
                        .limit(1)
                        .execute()
                    )

                    if not messages.data:
                        logger.warning(
                            f"⏭️ Manteniendo conversación sin mensajes: {conv['id']}"
                        )
                        continue

                    # Proceder con archivado y creación solo si hay mensajes
                    conv_id = conv["id"]
                    waba_id = conv["waba_id"]

                    logger.warning(f"📁 Archivando conversación: {conv_id}")

                    # Archivar conversación actual
                    self.supabase.table("conversations").update(
                        {
                            "status": "archived",
                            "archived_at": now.isoformat(),
                            "last_activity_at": now.isoformat(),
                            "metadata": {
                                "archive_reason": "development_reset",
                                "archived_at": now.isoformat(),
                            },
                        }
                    ).eq("id", conv_id).execute()

                    # Crear nueva conversación
                    new_conv = (
                        self.supabase.table("conversations")
                        .insert(
                            {
                                "waba_id": waba_id,
                                "phone_number": phone,
                                "status": "active",
                                "metadata": {
                                    "created_by": "development_reset",
                                    "created_at": now.isoformat(),
                                    "previous_conversation": conv_id,
                                },
                            }
                        )
                        .execute()
                    )

                    new_conv_id = new_conv.data[0]["id"]
                    logger.warning(f"✨ Nueva conversación creada: {new_conv_id}")

            logger.warning("✅ SINCRONIZACIÓN COMPLETADA")

        except Exception as e:
            logger.error(f"❌ Error en sincronización: {str(e)}", exc_info=True)
