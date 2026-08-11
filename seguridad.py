import time
from collections import deque
from captcha import registrar_solicitud_pendiente

# Lista de frases clave para detectar copias de mensajes oficiales del bot
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
                # Borramos el mensaje pegado
                bot.delete_message(message.chat.id, message.message_id)
            except Exception:
                pass
            return True  # Devuelve True indicando que era una copia detectada

    return False
    
def es_administrador(bot, chat_id, user_id, user=None):
    # 1. Si es CREADOR o Admin VIP directo por lista local (ID o Username)
    if user and es_admin_vip(bot, user):
        return True

    user_str = str(user_id).lower()
    admins_vip_lower = [str(u).lower() for u in ADMINS_VIP]
    if user_str in admins_vip_lower:
        return True

    # 2. Verificación en el CANAL PRINCIPAL (@COMUNIDADAS04)
    try:
        member_canal = bot.get_chat_member(CANAL_CONGESTIONADO, user_id)
        if member_canal.status in ['administrator', 'creator']:
            return True
    except Exception as e:
        print(f"Error consultando admin en canal principal: {e}")

    # 3. Verificación si es Admin del GRUPO ACTUAL (Por si tienes admins locales en el grupo)
    try:
        if isinstance(chat_id, int) and chat_id < 0:
            member = bot.get_chat_member(chat_id, user_id)
            if member.status in ['administrator', 'creator']:
                return True
    except Exception:
        pass

    # Si no es admin de ningún lado, devuelve False
    return False
    
# ============================================
# CONFIGURACIÓN DE ROLES Y EXCEPCIONES VIP
# ============================================

# Lista de administradores VIP (convertidos a minúsculas)
ADMINS_VIP = [ 
    "5073264705",
    "@antonys4", 
    "@papitamaster", 
    "@bazoner", 
    "@cristianobicicleteando", 
    "@nylebian",
    "@crisyfc",
    "@bunnyZ1234",
    "@cabezita24",
    "@daciani",
    "@kurohigexd",
    "@enriquecmoly",
    "@raudesikle",
    "@skyliarsz"
    
]

# Admin especial que requiere la tasa BCV con el 1% en Intervención
ADMIN_ESPECIAL_1_PORCIENTO = "@carloses783"


CANAL_CONGESTIONADO = -1001612840350
CANAL_ADMINS = -1003947562741

def es_admin_vip(bot, user):
    if not user:
        return False

    user_id = user.id
    username = f"@{user.username.lower()}" if user.username else ""

    # 1. VERIFICACIÓN INSTANTÁNEA (Lista local en memoria)
    admins_vip_lower = [str(u).lower() for u in ADMINS_VIP]
    if str(user_id) in admins_vip_lower or username in admins_vip_lower:
        return True

    # 2. ES ADMINISTRADOR DEL CANAL PRINCIPAL (@COMUNIDADAS04)
    try:
        miembro = bot.get_chat_member(CANAL_CONGESTIONADO, user_id)
        if miembro.status in ['administrator', 'creator']:
            return True
    except Exception:
        pass

    # 3. ES MIEMBRO DEL GRUPO CERRADO DE ADMINS (-1003947562741)
    try:
        miembro_grupo = bot.get_chat_member(CANAL_ADMINS, user_id)
        if miembro_grupo.status in ['member', 'administrator', 'creator']:
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


# Lista de comandos autorizados para el bot de administración (Group Help)
COMANDOS_GROUP_HELP = [
    "/reload", "/ban", "/mute", "/warn", 
    "/unban", "/unmute", "/info", "/config", "/start",
    "/aviso", "/aviso_captcha"
]

def limpiar_comandos_chat(bot, message):
    """
    Elimina los mensajes que empiecen con '/' para mantener el chat limpio.
    Permite un breve retraso para que Group Help procese la orden si es válida.
    """
    if not message or not message.text:
        return False

    texto = message.text.strip().lower()

    # Si el mensaje empieza con una barra diagonal '/'
    if texto.startswith("/"):
        # Extraemos solo el comando principal (ejemplo: '/ban' de '/ban 10 days')
        comando = texto.split()[0]

        # Si es un comando oficial de Group Help, esperamos medio segundo
        if comando in COMANDOS_GROUP_HELP:
            time.sleep(4)

        # Borramos el mensaje de texto del comando
        try:
            bot.delete_message(message.chat.id, message.message_id)
            return True
        except Exception:
            pass

    return False
    
def es_chat_permitido(bot, message, chats_permitidos, usuarios_autorizados, creador_id):
    if not message or not message.chat:
        return False

    chat_id = message.chat.id
    chat_username = f"@{message.chat.username}".lower() if message.chat.username else ""
    creador_str = str(creador_id)

    # 1. CHAT PRIVADO: Siempre permitido
    if message.chat.type == "private":
        return True

    # Convertimos los chats permitidos a strings/minúsculas para comparar con precisión
    permitidos_str = [str(c).lower() for c in chats_permitidos]

    # 2. GRUPOS/CANALES OFICIALES DE LA LISTA (Incluye CANAL_ADMINS, @COMUNIDADAS04, etc.)
    if str(chat_id) in permitidos_str or (chat_username and chat_username in permitidos_str):
        return True

    # 3. EXCEPCIÓN EN OTROS GRUPOS AJENOS:
    # Exige ESTRICTAMENTE que el Creador Supremo esté dentro del grupo y sea Admin/Propietario
    try:
        miembro_creador = bot.get_chat_member(chat_id, int(creador_id))
        if miembro_creador.status in ['creator', 'administrator']:
            return True
    except Exception:
        pass

    # Si no cumple ninguna de las anteriores, SILENCIO ABSOLUTO (Bloqueado)
    return False

# =======================================================================
# FILTRO ANTI-RAID Y CONTROL DE SOLICITUDES DE INGRESO (GATEKEEPER)
# =======================================================================
HISTORIAL_SOLICITUDES = deque(maxlen=30)

def registrar_filtro_anti_raid(bot):
    """
    Maneja las solicitudes de ingreso (chat_join_request) cuando el grupo
    está en privado con 'Aprobar nuevos miembros'.
    Filtra bots reteniendo cuentas sin foto/alias y frena ráfagas (raids).
    """
    @bot.chat_join_request_handler()
    def filtrar_solicitudes_entrada(request):
        user = request.from_user
        chat_id = request.chat.id
        ahora = time.time()

        # Registrar timestamp de la solicitud
        HISTORIAL_SOLICITUDES.append(ahora)

        # Detectar Ráfaga / Raid: 5 o más solicitudes en menos de 4 segundos
        solicitudes_recientes = [t for t in HISTORIAL_SOLICITUDES if ahora - t < 4]
        es_raid = len(solicitudes_recientes) >= 5

        # 🚨 SI HAY UN RAID EN PROCESO:
        if es_raid:
            # Notificar al grupo cerrado de Admins (solo una vez en el pico del ataque)
            if len(solicitudes_recientes) == 5:
                try:
                    bot.send_message(
                        CANAL_ADMINS,
                        "🚨 <b>¡ALERTA DE RAID DETECTADA!</b>\n"
                        "Se detectó una entrada masiva de solicitudes.\n"
                        "<i>Las aprobaciones automáticas se han pausado. Las solicitudes quedarán en espera para revisión manual.</i>",
                        parse_mode="HTML"
                    )
                except Exception:
                    pass
            # Queda retenido sin aprobar ni rechazar
            return
        
        # 🟢 SI NO ES RAID:
        # Registramos al usuario en la memoria del captcha
        registrar_solicitud_pendiente(bot, user.id, chat_id)





    
    
    
    
    
    
    
    
    
