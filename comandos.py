from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

# ==========================================
# CONFIGURACIÓN DE IDs Y PERMISOS
# ==========================================
# Tu ID numérico como Propietario
PROPIETARIO_ID = 5073264705  # <-- REEMPLAZA CON TU ID REAL

# Lista de IDs numéricos de tus Administradores
ADMINS_IDS = [
    8418460698,  # Carlos V <-- Reemplaza con los IDs de tus admins
    5470672620,  # Alejadro
    5971008307,  # dip
    6299629267,  # Osvaldo 
    693849279,   # sylar
    6422576568,  # J D
    7816422089   # Enderson secundario 
]


# ==========================================
# COMANDO /comandos
# ==========================================
async def comando_comandos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Muestra el manual de comandos jerarquizado por rangos y área de uso."""
    # Autodestruir el mensaje ejecutor del usuario
    try:
        await update.message.delete()
    except Exception:
        pass
      
    texto = (
        "<b>📋 GUÍA OFICIAL DE COMANDOS</b>\n\n"
        
        "<b>🥷🏽 PROPIETARIO (Uso exclusivo en Grupo):</b>\n"
        "▫️ <code>/aviso</code> ➡️ Pasos y resolución de Captcha para aprobación automática.\n"
        "▫️ <code>/ia</code> ➡️ Info del botón 🤖 IA Consulta, límites y rotación diaria.\n"
        "▫️ <code>/i</code> ➡️ Monitor de Intervención (Día actual y día siguiente).\n"
        "▫️ <code>/p</code> ➡️ Monitor P2P completo por rangos.\n"
        "▫️ <code>/zinli</code> ➡️ Monitor Zinli completo.\n"
        "▫️ <code>/bot</code> ➡️ Funciones del bot en su chat privado.\n"
        "▫️ <code>/tasa</code> ➡️ Monitor P2P Global.\n\n"
        
        "<b>👮🏽‍♂️ ADMINISTRADORES (Comandos para el Grupo):</b>\n"
        "▫️ <code>/aviso</code>\n"
        "▫️ <code>/zinli</code>\n"
        "▫️ <code>/i</code>\n"
        "▫️ <code>/p</code>\n"
        "▫️ <code>/tasa</code>\n\n"
        
        "<b>👤 USUARIOS ACTIVOS DEL GRUPO:</b>\n"
        "Uso directo de sus 9 botones en el chat interno del bot.\n\n"
        
        "<b>🤖 Comandos en Chat Privado del Bot (Alternativa):</b>\n"
        "▫️ <code>/i</code> ➡️ Monitor de Intervención.\n"
        "▫️ <code>/p</code> ➡️ Monitor P2P <i>(Usa este botón con la 📜 Regla de Oro 📜)</i>\n"
        "▫️ <code>/bp</code> ➡️ Guía práctica de uso sobre BPay.\n"
        "▫️ <code>/gp</code> ➡️ Guía práctica de uso sobre GPay.\n\n"
        "───────────────\n"
        "<i>Usa /comandos para consultar este panel cuando lo necesites.</i>"
    )
    
    await context.bot.send_message(
        chat_id=update.effective_chat.id, 
        text=texto, 
        parse_mode=ParseMode.HTML
    )


# ==========================================
# COMANDO /admin
# ==========================================
async def comando_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Obtiene los nombres de Telegram del Propietario y Admins mediante su ID."""
    # Autodestruir el mensaje ejecutor del usuario
    try:
        await update.message.delete()
    except Exception:
        pass
      
    bot = context.bot
    chat_id = update.effective_chat.id

    # 1. Mención dinámica del Propietario
    try:
        user_prop = await bot.get_chat_member(chat_id, PROPIETARIO_ID)
        nombre_prop = user_prop.user.first_name
    except Exception:
        nombre_prop = "Propietario"

    mencion_propietario = f'<a href="tg://user?id={PROPIETARIO_ID}">{nombre_prop}</a>'

    # 2. Mención dinámica de los Administradores
    menciones_admins = []
    for admin_id in ADMINS_IDS:
        try:
            user_admin = await bot.get_chat_member(chat_id, admin_id)
            nombre_admin = user_admin.user.first_name
            menciones_admins.append(f'▫️ <a href="tg://user?id={admin_id}">{nombre_admin}</a>')
        except Exception:
            # Respaldo si el bot no puede consultar el nombre en ese momento
            menciones_admins.append(f'▫️ <a href="tg://user?id={admin_id}">Admin [{admin_id}]</a>')

    lista_admins_texto = "\n".join(menciones_admins) if menciones_admins else "<i>No hay administradores configurados.</i>"

    # 3. Construcción del mensaje final
    texto = (
        "<b>🛡️ EQUIPO DE ADMINISTRACIÓN</b>\n\n"
        f"<b>🥷🏽 Propietario:</b>\n"
        f"👑 {mencion_propietario}\n\n"
        f"<b>👮🏽‍♂️ Administradores:</b>\n"
        f"{lista_admins_texto}\n\n"
        "───────────────\n"
        "<i>Si necesitas asistencia, contacta a cualquiera de nuestros administradores activos.</i>"
    )

    await context.bot.send_message(
        chat_id=update.effective_chat.id, 
        text=texto, 
        parse_mode=ParseMode.HTML
    )
