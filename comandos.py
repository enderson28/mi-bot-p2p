import telebot
from emojis import TG_EMOJIS, e

PROPIETARIO_ID = 5073264705  # Tu ID

ADMINS_IDS = [
    8418460698,  # Carlos
    5470672620, # Alejandro
    5971008307, # dip
    6299629267, # Osvaldo
    693849279,  # Sylar
    6422576568, # J D
    7816422089, # Enderson secundario
    1676933074  #Antony
]

def comando_comandos(bot, message):
    # Autodestruir el mensaje ejecutor /comandos
    try:
        bot.delete_message(message.chat.id, message.message_id)
    except Exception:
        pass

    texto = (
        f"<blockquote>{e('GUIAS', '❇️')} <b>GUÍA OFICIAL DE COMANDOS</b></blockquote>\n\n"
        f"<blockquote>{e('PROGRAMADOR', '❇️')} <b>PROPIETARIO (Uso exclusivo en Grupo):</b></blockquote>\n"
        f"───────────────\n"
        f"▫️ <code>/aviso</code> {e('FLECHA_DERECHA', '❇️')} {e('PASOS', '❇️')} Pasos y resolución de Captcha {e('CAPTCHA', '❇️')} para aprobación automática.\n"
        f"───────────────\n"
        f"▫️ <code>/ia</code> {e('FLECHA_DERECHA', '❇️')}  {e('GUIAS', '❇️')} Info del botón 🤖 IA Consulta, límites y rotación diaria.\n"
        f"───────────────\n"
        f"▫️ <code>/i</code> {e('FLECHA_DERECHA', '❇️')} {e('BCV', '❇️')} Monitor de Intervención (Día actual y día siguiente).\n"
        f"───────────────\n"
        f"▫️ <code>/p</code> {e('FLECHA_DERECHA', '❇️')}  {e('BINANCE_ESPEJO', '❇️')} Monitor P2P completo por rangos.\n"
        f"───────────────\n"
        f"▫️ <code>/zinli</code> {e('FLECHA_DERECHA', '❇️')} {e('zinli', '❇️')} Monitor Zinli completo.\n"
        f"───────────────\n"
        f"▫️ <code>/bot</code> {e('FLECHA_DERECHA', '❇️')} {e('ROBOTICO', '❇️')} Funciones del bot en su chat privado.\n"
        f"───────────────\n"
        f"▫️ <code>/brecha</code> {e('FLECHA_DERECHA', '❇️')} {e('USDT', '❇️')}/{e('ROJO', '❇️')} Brecha entre VENTA y BCV 0.5%\n"
        f"───────────────\n"
        f"▫️ <code>/tasa</code> {e('FLECHA_DERECHA', '❇️')} {e('BINANCE_P2P', '❇️')} Monitor P2P Global.\n\n"
        
        f"<blockquote>{e('REVISION', '❇️')} <b>ADMINISTRADORES (Comandos para el Grupo):</b>\n</blockquote>"
        f"▫️ <code>/aviso</code>\n"
        f"▫️ <code>/zinli</code>\n"
        f"▫️ <code>/i</code>\n"
        f"▫️ <code>/p</code>\n"
        f"▫️ <code>/brecha</code>\n"
        f"▫️ <code>/tasa</code>\n\n"
        
        f"<blockquote>{e('BOTS', '❇️')} <b>USUARIOS ACTIVOS DEL GRUPO:</b></blockquote>\n"
        f"───────────────\n"
        f"Uso directo de sus 9 botones en el chat interno del bot.\n\n"
        
        f"{e('ROBOTICO', '❇️')} <b>Comandos en Chat Privado del Bot (Alternativa):</b>\n"
        f"───────────────\n"
        f"▫️ <code>/i</code> {e('FLECHA_DERECHA', '❇️')} Monitor de Intervención.\n"
        f"───────────────\n"
        f"▫️ <code>/p</code> {e('FLECHA_DERECHA', '❇️')} Monitor P2P <i>(Usa este botón con la 📜 Regla de Oro 📜)</i>\n"
        f"───────────────\n"
        f"▫️ <code>/bp</code> {e('FLECHA_DERECHA', '❇️')} Guía práctica de uso sobre BPay.\n"
        f"▫️ <code>/gp</code> {e('FLECHA_DERECHA', '❇️')} Guía práctica de uso sobre GPay.\n\n"
        f"───────────────\n"
        f"{e('clic', '❇️')}<i>Usa /comandos para consultar este panel cuando lo necesites.</i>"
    )
    
    bot.send_message(message.chat.id, texto, parse_mode="HTML")


def comando_admin(bot, message):
    # Autodestruir el mensaje ejecutor /admin
    try:
        bot.delete_message(message.chat.id, message.message_id)
    except Exception:
        pass

    chat_id = message.chat.id

    # 1. Mención dinámica del Propietario
    try:
        user_prop = bot.get_chat_member(chat_id, PROPIETARIO_ID)
        nombre_prop = user_prop.user.first_name
    except Exception:
        nombre_prop = "Propietario"

    mencion_propietario = f'<a href="tg://user?id={PROPIETARIO_ID}">{nombre_prop}</a>'

    # 2. Mención dinámica de los Administradores
    menciones_admins = []
    for admin_id in ADMINS_IDS:
        try:
            user_admin = bot.get_chat_member(chat_id, admin_id)
            nombre_admin = user_admin.user.first_name
            menciones_admins.append(f'▫️ <a href="tg://user?id={admin_id}">{nombre_admin}</a>')
        except Exception:
            menciones_admins.append(f'▫️ <a href="tg://user?id={admin_id}">Admin [{admin_id}]</a>')

    lista_admins_texto = "\n".join(menciones_admins) if menciones_admins else "<i>No hay administradores configurados.</i>"

    # 3. Construcción del mensaje final
    texto = (
        f"{e('ESCUDO', '❇️')} <b>EQUIPO DE ADMINISTRACIÓN</b>\n\n"
        f"{e('PROGRAMADOR', '❇️')} <b>Propietario:</b>\n"
        f"👑 {mencion_propietario}\n\n"
        f"{e('REVISION', '❇️')} <b>Administradores:</b>\n"
        f"{lista_admins_texto}\n\n"
        f"───────────────\n"
        f"<i>Si necesitas asistencia, {e('pago_movil', '❇️')} contacta a cualquiera de nuestros administradores activos.</i>"
    )

    bot.send_message(chat_id, texto, parse_mode="HTML")
    
