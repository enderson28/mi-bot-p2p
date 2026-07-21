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
    if user and es_admin_vip(user):
        return True

    # 2. Si es Administrador o Creador en el grupo/chat actual
    try:
        member = bot.get_chat_member(chat_id, user_id)
        if member.status in ['administrator', 'creator']:
            return True
    except Exception:
        pass

    # 3. Verifica si es Administrador del CANAL PRINCIPAL
    try:
        canal_principal = "@COMUNIDADAS04"
        member_canal = bot.get_chat_member(canal_principal, user_id)
        if member_canal.status in ['administrator', 'creator']:
            return True
    except Exception:
        pass

    # Si no cumple ninguna de las 3, es un usuario común
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


def es_admin_vip(user):
    """Verifica si un usuario es Admin VIP por su ID o Username"""
    if not user:
        return False
    
    user_id = user.id
    username = f"@{user.username.lower()}" if user.username else ""
    
    # Compara tanto el ID numérico como el username en minúsculas
    return (user_id in ADMINS_VIP) or (username.lower() in [u.lower() for u in ADMINS_VIP])


def es_admin_especial(user):
    """Verifica si es el admin que requiere el 1%"""
    if not user:
        return False
    
    user_id = str(user.id)
    username = f"@{user.username.lower()}" if user.username else ""
    admin_especial = ADMIN_ESPECIAL_1_PORCIENTO.lower()
    
    return (user_id == admin_especial) or (username == admin_especial)

    
    
