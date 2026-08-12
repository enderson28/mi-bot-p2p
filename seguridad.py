import time
from collections import deque
from captcha import registrar_solicitud_pendiente

# =========================================================
# LISTA NEGRA GLOBAL (BLOQUEO ABSOLUTO)
# =========================================================
# Dejada completamente vacía para evitar bloqueos accidentales
LISTA_NEGRA = []

def es_lista_negra(user):
    """Devuelve True si el usuario o su ID están en la lista negra global."""
    if not user:
        return False

    user_id = str(user.id)
    username = f"@{user.username.lower()}" if getattr(user, 'username', None) else ""

    lista_lower = [str(u).lower() for u in LISTA_NEGRA]

    if user_id in lista_lower or (username and username in lista_lower):
        return True

    return False

# =========================================================
# PROTECCIÓN CONTRA COPIA Y PEGA DE CONTENIDO
# =========================================================
FRASES_PROHIBIDAS = [
    # Reportes y Monitores Oficiales
    "monitor de tasas",
    "vigencia bcv",
    "bcv oficial",
    "calculadora de intervención",
    "intervención bancaria",
    "spread:",

    # Mensaje de invitación (/bot) y mensajes automáticos
    "aprovecha al máximo las herramientas del bot",
    "consulta en privado sin límites",

    # Mensaje automático de 6 horas (anuncios.py)
    "consulta las tasas y guías en privado",
    "para mantener el grupo libre de spam",

    # Avisos de restricción y autoría
    "comando exclusivo para administradores",
    "comando exclusivo del creador del bot"
]

def validar_copia_pega(bot, message, es_admin):
    """
    Si un usuario normal pega cualquier texto oficial del bot o sus reportes,
    el bot borra el mensaje de inmediato para evitar spam o confusión.
    """
    # 0. Ignorar publicaciones reenviadas automáticamente desde el canal oficial
    if getattr(message, 'is_automatic_forward', False):
        return False

    # 1. Si es Administrador, lo dejamos hablar tranquilamente
    if es_admin:
        return False

    # 2. Convertimos el texto del mensaje a minúsculas para comparar
    texto = message.text.lower() if message and message.text else ""

    # 3. Verificamos si contiene alguna frase prohibida
    for frase in FRASES_PROHIBIDAS:
        if frase in texto:
            try:
                bot.delete_message(message.chat.id, message.message_id)
            except Exception:
                pass
            return True

    return False

# =========================================================
# GESTIÓN Y VERIFICACIÓN DE ADMINISTRADORES
# =========================================================
def es_administrador(bot, chat_id, user_id, user=None):
    # BLINDAJE PRIORITARIO: Si está en la lista negra, no es admin
    if user and es_lista_negra(user):
        return False

    # 1. Si es CREADOR o Admin VIP directo por lista local
    if user and es_admin_vip(bot, user):
        return True

    user_str = str(user_id).lower()
    admins_vip_lower = [str(u).lower() for u in ADMINS_VIP]
    if user_str in admins_vip_lower:
        return True

    # 2. Verificación en el GRUPO PRINCIPAL
    try:
        member_canal = bot.get_chat_member(CANAL_PRUEBA, user_id)
        if member_canal.status in ['administrator', 'creator']:
            return True
    except Exception as e:
        print(f"Error consultando admin en canal principal: {e}")

    # 3. Verificación si es Admin del GRUPO ACTUAL
    try:
        if isinstance(chat_id, int) and chat_id < 0:
            member = bot.get_chat_member(chat_id, user_id)
            if member.status in ['administrator', 'creator']:
                return True
    except Exception:
        pass

    return False

# =========================================================
# CONFIGURACIÓN DE ROLES Y EXCEPCIONES VIP
# =========================================================

# Solo dejamos el ID del Creador Principal en VIP
ADMINS_VIP = [
    "5073264705",   # Enderson Principal
]

ADMIN_ESPECIAL_1_PORCIENTO = "8418460698"

CANAL_PRUEBA = -1004473532809
CANAL_PRINCIPAL_IDV = -1003950050807

def es_admin_vip(bot, user):
    if not user:
        return False

    if es_lista_negra(user):
        return False

    user_id = user.id
    username = f"@{user.username.lower()}" if user.username else ""

    # 1. VERIFICACIÓN INSTANTÁNEA (Lista local)
    admins_vip_lower = [str(u).lower() for u in ADMINS_VIP]
    if str(user_id) in admins_vip_lower or username in admins_vip_lower:
        return True

    # 2. ES ADMINISTRADOR DEL GRUPO PRINCIPAL
    try:
        miembro = bot.get_chat_member(CANAL_PRUEBA, user_id)
        if miembro.status in ['administrator', 'creator']:
            return True
    except Exception:
        pass

    return False

def es_admin_especial(user):
    """Verifica si es el admin que requiere el 1%"""
    if not user:
        return False

    user_id = str(user.id)
    username = f"@{user.username.lower()}" if user.username else ""
    admin_especial = ADMIN_ESPECIAL_1_PORCIENTO.lower()

    return (user_id == admin_especial) or (username == admin_especial)

# =========================================================
# LIMPIEZA DE COMANDOS Y PERMISOS DE CHAT
# =========================================================
COMANDOS_GROUP_HELP = [
    "/reload", "/ban", "/mute", "/warn",
    "/unban", "/unmute", "/info", "/config", "/start"
]

def limpiar_comandos_chat(bot, message):
    if not message or not message.text:
        return False

    texto = message.text.strip().lower()

    if texto.startswith("/aviso") or texto.startswith("/aviso_captcha"):
        return False

    if texto.startswith("/"):
        comando = texto.split()[0]

        if comando in COMANDOS_GROUP_HELP:
            time.sleep(4)
            try:
                bot.delete_message(message.chat.id, message.message_id)
                return True
            except Exception:
                pass

    return False

def es_chat_permitido(bot, message, chats_permitidos, usuarios_autorizados, creador_id):
    if not message or not message.chat:
        return False

    # BLINDAJE PRIORITARIO: Si la orden viene de lista negra, ignora totalmente
    if message.from_user and es_lista_negra(message.from_user):
        return False

    chat_id = message.chat.id
    chat_username = f"@{message.chat.username}".lower() if message.chat.username else ""

    # 1. CHAT PRIVADO: Siempre permitido
    if message.chat.type == "private":
        return True

    permitidos_str = [str(c).lower() for c in chats_permitidos]

    # 2. GRUPOS/CANALES OFICIALES DE LA LISTA
    if str(chat_id) in permitidos_str or (chat_username and chat_username in permitidos_str):
        return True

    # 3. EXCEPCIÓN EN OTROS GRUPOS AJENOS
    try:
        miembro_creador = bot.get_chat_member(chat_id, int(creador_id))
        if miembro_creador.status in ['creator', 'administrator']:
            return True
    except Exception:
        pass

    return False

# =========================================================
# FILTRO ANTI-RAID Y CONTROL DE SOLICITUDES DE INGRESO
# =========================================================
HISTORIAL_SOLICITUDES = deque(maxlen=30)

def registrar_filtro_anti_raid(bot):
    """Maneja las solicitudes de ingreso cuando el grupo está en privado."""

    @bot.chat_join_request_handler()
    def filtrar_solicitudes_entrada(request):
        user = request.from_user
        chat_id = request.chat.id
        ahora = time.time()

        HISTORIAL_SOLICITUDES.append(ahora)

        solicitudes_recientes = [t for t in HISTORIAL_SOLICITUDES if ahora - t < 4]
        es_raid = len(solicitudes_recientes) >= 5

        if es_raid:
            if len(solicitudes_recientes) == 5:
                try:
                    bot.send_message(
                        CANAL_PRUEBA,
                        "🚨 <b>ALERTA DE RAID DETECTADA!</b>\n"
                        "Se detectó una entrada masiva de solicitudes.\n"
                        "<i>Las aprobaciones automáticas se han pausado. Las solicitudes quedarán en espera.</i>",
                        parse_mode="HTML"
                    )
                except Exception:
                    pass
            return

        registrar_solicitud_pendiente(bot, user.id, chat_id)

def registrar_limpiador_servicio(bot):
    """Borra automáticamente avisos de entrada o salida de usuarios"""

    @bot.message_handler(content_types=['new_chat_members', 'left_chat_member'])
    def borrar_mensajes_servicio(message):
        try:
            bot.delete_message(message.chat.id, message.message_id)
        except Exception:
            pass
            
