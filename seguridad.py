import threading

# ==========================================
# CONFIGURACIÓN DE ROLES Y EXCEPCIONES VIP
# ==========================================

OWNER_ID = int(os.getenv("OWNER_ID", "5073264705"))

ADMINS_VIP = [
    "5073264705",   # Enderson Principal
    "1676933074",   # Antony
    "1920750484",   #Cr7
    "8166481937",   #cilita
    "6299629267",   #Osvaldo osito
    "7616851192",   #Chino
    "8757407672",   #Cris
    "7249758098",   #Conejo
    "1746316458",   #Cucu
    "8971327009",   #Maxi
    "6107750160",   #Kuro
    "5103278703"   #Kilómetro 
]

ADMIN_ESPECIAL_1_PORCIENTO = "8418480698"

# ID del grupo nuevo exclusivo del bot secundario
CANAL_PRUEBA = -1001612248350


# ==========================================
# GESTIÓN Y VERIFICACIÓN DE ADMINISTRADORES
# ==========================================

def es_admin_vip(bot, user):
    """Verifica si el usuario está en la lista de Admins VIP exentos de pago."""
    if not user:
        return False

    if es_lista_negra(user):
        return False

    user_id = str(user.id)
    username = f"@{user.username.lower()}" if getattr(user, "username", None) else ""
    admins_vip_lower = [str(u).lower() for u in ADMINS_VIP]

    if user_id == str(OWNER_ID) or user_id in admins_vip_lower or (username and username in admins_vip_lower):
        return True

    return False


def es_administrador(bot, chat_id, user_id, user=None):
    # BLINDAJE PRIORITARIO: Si está en lista negra, no es admin
    if user and es_lista_negra(user):
        return False

    # 1. Si es CREADOR o Admin VIP directo por lista local
    if user and es_admin_vip(bot, user):
        return True

    user_str = str(user_id).lower()
    admins_vip_lower = [str(u).lower() for u in ADMINS_VIP]
    if user_str == str(OWNER_ID) or user_str in admins_vip_lower:
        return True

    # 2. Verificación en el GRUPO OFICIAL ASIGNADO
    try:
        member_canal = bot.get_chat_member(CANAL_PRUEBA, user_id)
        if member_canal.status in ["administrator", "creator"]:
            return True
    except Exception as e:
        print(f"Error consultando admin en grupo oficial: {e}")

    # 3. Verificación si es Admin del GRUPO ACTUAL
    try:
        if isinstance(chat_id, int) and chat_id < 0:
            member = bot.get_chat_member(chat_id, user_id)
            if member.status in ["administrator", "creator"]:
                return True
    except Exception:
        pass

    return False


def es_admin_especial(user):
    """Verifica si es el admin que requiere el 1%"""
    if not user:
        return False

    user_id = str(user.id)
    username = f"@{user.username.lower()}" if getattr(user, "username", None) else ""
    admin_especial = ADMIN_ESPECIAL_1_PORCIENTO.lower()

    return (user_id == admin_especial) or (username == admin_especial)


# ==========================================
# LIMPIEZA DE COMANDOS Y PERMISOS DE CHAT
# ==========================================

COMANDOS_GROUP_HELP = [
    "/reload", "/ban", "/mute", "/warn",
    "/unban", "/unmute", "/info", "/config", "/start", "/rules", "/staff"
]


def _borrar_mensaje_diferido(bot, chat_id, message_id):
    try:
        bot.delete_message(chat_id, message_id)
    except Exception:
        pass


def limpiar_comandos_chat(bot, message):
    if not message or not message.text:
        return False

    texto = message.text.strip().lower()

    if texto.startswith("/aviso") or texto.startswith("/aviso_captcha"):
        return False

    if texto.startswith("/"):
        comando = texto.split()[0].split("@")[0]

        if comando in COMANDOS_GROUP_HELP:
            # Borrado no bloqueante tras 5 segundos para que Group Help procese primero
            timer = threading.Timer(5.0, _borrar_mensaje_diferido, args=(bot, message.chat.id, message.message_id))
            timer.daemon = True
            timer.start()
            return True

    return False


def es_chat_permitido(bot, message, chats_permitidos, usuarios_autorizados, creador_id):
    if not message or not message.chat:
        return False

    # BLINDAJE PRIORITARIO: Si la orden viene de lista negra, ignora totalmente
    if message.from_user and es_lista_negra(message.from_user):
        return False

    chat_id = message.chat.id
    chat_username = f"@{message.chat.username.lower()}" if getattr(message.chat, "username", None) else ""

    # 1. CHAT PRIVADO: Siempre permitido (el acceso VIP se filtra luego por comando/botón)
    if message.chat.type == "private":
        return True

    # 2. EXCLUSIVIDAD: Solo el grupo autorizado en chats_permitidos / CANAL_PRUEBA
    permitidos_str = [str(c).lower() for c in chats_permitidos]
    if str(CANAL_PRUEBA) not in permitidos_str:
        permitidos_str.append(str(CANAL_PRUEBA))

    if str(chat_id) in permitidos_str or (chat_username and chat_username in permitidos_str):
        return True

    return False


# ==========================================
# VERIFICACIÓN DE ACCESO VIP (REDIS + EXCEPCIÓN ADMINS_VIP)
# ==========================================

def es_usuario_vip_activo(bot, user, r):
    if not user:
        return False

    if es_lista_negra(user):
        return False

    # El Creador y los ADMINS_VIP NUNCA pagan (excepción directa)
    if user.id == OWNER_ID or es_admin_vip(bot, user):
        return True

    if not r:
        return False

    key = f"vip_user:{user.id}"

    # Si se le pasa la conexión de Redis directamente
    if hasattr(r, "exists"):
        return bool(r.exists(key))

    # Si se le pasa un diccionario de caché
    if isinstance(r, dict):
        return key in r and r.get(key) is not None

    return False


def responder_sin_acceso_vip(bot, chat_id):
    """Envía el panel de suscripción VIP con la botonera de 3 pasos."""
    markup = InlineKeyboardMarkup(row_width=1)

    btn_solicitar = InlineKeyboardButton(
        "📩 Enviar Solicitud VIP",
        callback_data="solicitar_vip_pago"
    )

    btn_soporte = InlineKeyboardButton(
        "💳 Soporte / Datos de Pago",
        callback_data="ver_soporte_vip"
    )

    btn_comprobante = InlineKeyboardButton(
        "📤 Enviar Comprobante al Creador",
        url="https://t.me/+584145057892"
    )

    markup.add(btn_solicitar, btn_soporte, btn_comprobante)

    texto = (
        "🔒 <b>Contenido Exclusivo VIP</b>\n\n"
        "Esta herramienta requiere una suscripción activa.\n"
        "Tarifa mínima: <b>2 USDT / Quincenal</b> (o equivalente en Bs).\n\n"
        "<b>Pasos para activarlo:</b>\n"
        "1. Presiona <b>Enviar Solicitud VIP</b> para notificar al sistema.\n"
        "2. Consulta las cuentas en <b>💳 Soporte / Datos de Pago</b>.\n"
        "3. Envía el captura en <b>Enviar Comprobante</b>."
    )

    bot.send_message(chat_id, texto, parse_mode="HTML", reply_markup=markup)


