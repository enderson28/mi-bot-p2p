import time
import threading

# ⏱️ Configuración de tiempos
INTERVALO_HORAS = 2          # Frecuencia con la que se publica el anuncio automático
DURACION_VISIBLE_MIN = 15     # Minutos que permanece visible antes de borrarse


def obtener_texto_anuncio():
    """Construye el texto enriquecido de forma 100% compatible con HTML de Telegram."""
    return (
        "🛡️ <b>¡SISTEMA DE VERIFICACIÓN Y SEGURIDAD!</b> 🛡️\n\n"
        "🚨 Para mantener la comunidad libre de spam, bots y cuentas falsas, tenemos activo un captcha de entrada.\n\n"
        "Si solicitaste ingreso y tu solicitud sigue <b>pendiente</b>, sigue estos pasos:\n"
        "1️⃣ 🤖 Entra al chat privado de nuestro bot: @{BOT_USERNAME}\n"
        "2️⃣ ⚡ Presiona el botón <b>INICIAR</b> o envía <code>/start</code>.\n"
        "3️⃣ ✔️ Resuelve la suma matemática súper sencilla.\n\n"
        "⏳ <b>¡IMPORTANTE!</b> Dispones de <b>1 hora</b> desde que solicitas tu entrada para resolver la verificación o la solicitud será rechazada automáticamente(aunque puedes volver a solicitarla cuando gustes).\n\n"
        "<i>💡 Este mensaje se autodestruirá en 15 minutos para mantener el chat limpio.</i>"
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

    # Espera inicial de 3 minutos al encender el bot antes del primer anuncio automático
    time.sleep(180)

    while True:
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

        # Espera las horas configuradas antes de la próxima ronda
        time.sleep(segundos_espera)


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

        # 🔒 Filtro de seguridad: Solo Creador o Admins VIP
        if not funcion_es_admin_vip(bot, user) and user.id not in usuarios_autorizados:
            try:
                bot.delete_message(chat_id, message.message_id)
            except Exception:
                pass
            return

        try:
            # 1. Borra el comando escrito por el admin (/aviso) para mantener el chat limpio
            try:
                bot.delete_message(chat_id, message.message_id)
            except Exception:
                pass

            # 2. Envía el aviso estilizado
            texto = obtener_texto_anuncio()
            msg = bot.send_message(
                chat_id, 
                texto, 
                parse_mode="HTML", 
                disable_web_page_preview=True
            )
            
            # 3. Lo programa para borrar en 10 minutos (600 seg)
            _eliminar_mensaje_luego(bot, chat_id, msg.message_id, 600)

        except Exception as e:
            print(f"⚠️ Error al ejecutar comando manual /aviso: {e}")
            
