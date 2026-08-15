import time
import threading
from emojis import TG_EMOJIS, e

# ⏱️ Configuración de tiempos
INTERVALO_HORAS = 2          # Frecuencia del anuncio automático (2 horas)
DURACION_VISIBLE_MIN = 15     # Minutos visible antes de borrarse


def obtener_texto_anuncio():
    """Construye el texto enriquecido de forma 100% compatible con HTML de Telegram."""
    return (
        f"{e('ESCUDO', '🛡️')} <b>¡SISTEMA DE VERIFICACIÓN Y SEGURIDAD!</b> {e('ESCUDO', '🛡️')}\n\n"
        f"{e('SIRENA', '🚨')} Para mantener la comunidad libre de {e('SPAM', '🧹')} , {e('BOTS', '⌨️')} bots y {e('CUENTAS_FALSAS', '✍️')} cuentas falsas, tenemos activo un captcha {e('CAPTCHA', '🗯️')} de entrada.\n\n"
        f"Si {e('SOLICITUD', '😶‍🌫️')} solicitaste ingreso y tu solicitud sigue {e('PENDIENTE', '🗃️')} <b>pendiente</b>, sigue estos pasos {e('PASOS', '🦶')} :\n"
        f"{e('NUMERO1', '1️⃣')} {e('ROBOTICO', '👏🏼')} Entra al chat privado de nuestro bot: @BancoIDV_bot\n"
        f"{e('NUMERO2', '2️⃣')} {e('clic', '🎯')} Presiona el botón <b>INICIAR</b> o envía <code>/start</code>.\n"
        f"{e('NUMERO3', '3️⃣')} {e('check', '✔️')} Resuelve la suma matemática súper sencilla.\n\n"
        f"{e('ARENITA', '☄️')} <b>¡IMPORTANTE!</b> Dispones de <b>1 hora</b> desde que solicitas tu entrada para resolver la verificación o la solicitud será {e('RECHAZO', '👎')} rechazada automáticamente (puedes volver a hacer la solicitud cuando gustes 👏🏼).\n\n"
        f"{e('BOOM', '💥')} <i>Este mensaje se autodestruirá en 15 minutos para mantener el chat limpio.</i>\n"
        f"-----------------------------------------------------------\n"
    )


def _eliminar_mensaje_luego(bot, chat_id, message_id, segundos):
    """Función interna para borrar el anuncio tras X segundos."""
    def eliminar():
        time.sleep(segundos)
        try:
            bot.delete_message(chat_id, message_id)
        except Exception:
            pass
    threading.Thread(target=eliminar, daemon=True).start()


def bucle_anuncios(bot, lista_chats):
    """Bucle infinito que envía el anuncio a cada canal/grupo en lista_chats."""
    segundos_espera = INTERVALO_HORAS * 3600
    segundos_visibles = DURACION_VISIBLE_MIN * 60

    while True:
        # Espera las 2 horas completas ANTES de enviar el anuncio
        time.sleep(segundos_espera)

        texto = obtener_texto_anuncio()
        for chat_id in lista_chats:
            try:
                msg = bot.send_message(
                    chat_id, 
                    texto, 
                    parse_mode="HTML", 
                    disable_web_page_preview=True
                )
                print(f"📢 Anuncio automático enviado con éxito a {chat_id}")
                
                # Programa la autodestrucción tras 15 minutos
                _eliminar_mensaje_luego(bot, chat_id, msg.message_id, segundos_visibles)

            except Exception as e:
                print(f"⚠️ Error al enviar el anuncio automático a {chat_id}: {e}")


def iniciar_modulo_anuncios(bot, lista_chats):
    """Inicia el hilo secundario para los anuncios automáticos."""
    hilo = threading.Thread(target=bucle_anuncios, args=(bot, lista_chats), daemon=True)
    hilo.start()
    print("📢 Módulo de anuncios automáticos activado correctamente.")


def setup_comando_aviso(bot, funcion_es_admin_vip, usuarios_autorizados):
    """Registra el comando manual /aviso o /aviso_captcha para Administradores."""
    
    @bot.message_handler(commands=['aviso', 'aviso_captcha'])
    def handle_aviso_manual(message):
        user = message.from_user
        chat_id = message.chat.id

        # 🔒 1. Verificar si es Admin del grupo actual
        es_admin_del_chat = False
        if message.chat.type in ['group', 'supergroup']:
            try:
                miembro = bot.get_chat_member(chat_id, user.id)
                if miembro.status in ['administrator', 'creator']:
                    es_admin_del_chat = True
            except Exception:
                pass

        # 🔒 2. Verificar si es Admin VIP o Creador global
        es_admin_vip = funcion_es_admin_vip(bot, user)
        es_creador = user.id in usuarios_autorizados

        # Si no cumple NINGUNA de las condiciones, rechaza el comando
        if not (es_admin_del_chat or es_admin_vip or es_creador):
            try:
                bot.delete_message(chat_id, message.message_id)
            except Exception:
                pass
            return

        try:
            # Borra el comando escrito por el admin (/aviso)
            try:
                bot.delete_message(chat_id, message.message_id)
            except Exception:
                pass

            # Envía el anuncio
            texto = obtener_texto_anuncio()
            msg = bot.send_message(
                chat_id, 
                texto, 
                parse_mode="HTML", 
                disable_web_page_preview=True
            )
            
            # Programa borrado en 10 minutos (600 seg)
            _eliminar_mensaje_luego(bot, chat_id, msg.message_id, 600)

        except Exception as e:
            print(f"⚠️ Error al ejecutar comando manual /aviso: {e}")
                
