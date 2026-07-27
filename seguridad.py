import time
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
    # 1. Si está en la lista VIP/Especial manual
    if user and es_admin_vip(bot, user):
        return True

    # Si no trajo el objeto 'user', intentamos construir la validación VIP solo con el user_id
    if str(user_id) in [str(u) for u in ADMINS_VIP]:
        return True

    # 2. Si es chat privado (ID positivo) y no es VIP, es un usuario normal
    if isinstance(chat_id, int) and chat_id > 0:
        return False

    # 3. Si es un GRUPO, recién aquí consulta a Telegram si es Admin del grupo
    try:
        member = bot.get_chat_member(chat_id, user_id)
        if member.status in ['administrator', 'creator']:
            return True
    except Exception:
        pass

    # 4. Verifica si es Administrador del CANAL PRINCIPAL
    try:
        canal_principal = "@COMUNIDADAS04"
        member_canal = bot.get_chat_member(canal_principal, user_id)
        if member_canal.status in ['administrator', 'creator']:
            return True
    except Exception:
        pass

    return False
    
    
# ============================================
# CONFIGURACIÓN DE ROLES Y EXCEPCIONES VIP
# ============================================

# Lista de administradores VIP (convertidos a minúsculas)
ADMINS_VIP = [ 
    "@enderson28",
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


def es_admin_vip(bot, user, chat_canal="@COMUNIDADES04"):
    if not user:
        return False

    user_id = user.id
    username = f"@{user.username.lower()}" if user.username else ""

    # 1. VERIFICACIÓN INSTANTÁNEA (En memoria local, 0 milisegundos)
    admins_vip_lower = [str(u).lower() for u in ADMINS_VIP]

    if str(user_id) in admins_vip_lower or username in admins_vip_lower:
        return True
    
    # 2. Solo si NO está en la lista VIP local, le consulta a Telegram
    try:
        miembro = bot.get_chat_member(chat_canal, user_id)
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


# Lista de comandos autorizados para el bot de administración (Group Help)
COMANDOS_GROUP_HELP = [
    "/reload", "/ban", "/mute", "/warn", 
    "/unban", "/unmute", "/info", "/config"
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

    user_id = str(message.from_user.id) if message.from_user else ""
    creador_str = str(creador_id)

    # 1. SI TU ID NUMÉRICO COINCIDE O ERES ADMIN VIP, ACCESO TOTAL EN CUALQUIER LUGAR
    if user_id == creador_str or es_admin_vip(bot, message.from_user):
        return True

    # 2. CHAT PRIVADO
    if message.chat.type == "private":
        return True

    # 3. VERIFICACIÓN EN GRUPOS / CANALES PERMITIDOS
    chat_id = message.chat.id
    chat_username = f"@{message.chat.username}".lower() if message.chat.username else ""

    # Convertimos los permitidos a minúsculas y strings para evitar fallos de tipo (str vs int)
    permitidos_str = [str(c).lower() for c in chats_permitidos]

    if str(chat_id) in permitidos_str or (chat_username and chat_username in permitidos_str):
        return True

    # 4. EXCEPCIÓN DINÁMICA EN OTROS GRUPOS
    try:
        miembro_creador = bot.get_chat_member(chat_id, int(creador_id))
        if miembro_creador.status in ['creator', 'administrator']:
            return True
    except Exception:
        pass

    return False
    
    
    
    
    
    
    
    
