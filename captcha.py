import random
from telebot import types

pending_verifications = {}

def setup_verification_handlers(bot, target_channel_id):

    # 1. Escuchar solicitudes de ingreso al canal/grupo
    @bot.chat_join_request_handler(func=lambda req: req.chat.id == target_channel_id)
    def handle_join_request(req):
        user_id = req.from_user.id
        chat_id = req.chat.id
        
        pending_verifications[user_id] = {
            "chat_id": chat_id,
            "status": "pending"
        }
        
        try:
            bot.send_message(
                user_id,
                "👋 **¡Hola! Para completar tu ingreso al grupo, necesitas verificarte.**\n\n"
                "Usa el comando /verificar o presiona /start para resolver un sencillo Captcha.",
                parse_mode="Markdown"
            )
        except Exception:
            pass

    # 2. Comando /start y /verificar
    @bot.message_handler(commands=['verificar', 'start'])
    def start_verification(message):
        user_id = message.from_user.id
        
        # SI NO TIENE CAPTCHA PENDIENTE -> Muestra tu menú/bienvenida directo
        if user_id not in pending_verifications:
            mostrar_menu_bienvenida(bot, message.chat.id)
            return

        # SI TIENE CAPTCHA PENDIENTE -> Genera la suma
        num1 = random.randint(1, 9)
        num2 = random.randint(1, 9)
        correct_answer = str(num1 + num2)

        pending_verifications[user_id]["answer"] = correct_answer

        markup = types.InlineKeyboardMarkup(row_width=2)
        wrong_answers = set()
        while len(wrong_answers) < 3:
            fake = random.randint(2, 18)
            if str(fake) != correct_answer:
                wrong_answers.add(str(fake))

        all_options = list(wrong_answers) + [correct_answer]
        random.shuffle(all_options)

        buttons = [
            types.InlineKeyboardButton(opt, callback_data=f"captcha_{opt}")
            for opt in all_options
        ]
        markup.add(*buttons)  # <--- Sin comillas

        bot.send_message(
            user_id,
            f"🤖 **Verificación de Seguridad**\n\n"
            f"¿Cuánto es **{num1} + {num2}**?\n"
            f"Selecciona el botón correcto para aprobar tu entrada:",
            reply_markup=markup,
            parse_mode="Markdown"
        )

    # 3. Callback del Captcha
    @bot.callback_query_handler(func=lambda call: call.data.startswith("captcha_"))
    def process_captcha(call):
        user_id = call.from_user.id
        user_answer = call.data.split("_")[1]

        if user_id not in pending_verifications:
            bot.answer_callback_query(call.id, "No tienes ninguna verificación pendiente.")
            return

        expected_answer = pending_verifications[user_id].get("answer")
        chat_id = pending_verifications[user_id].get("chat_id")

        if user_answer == expected_answer:
            try:
                # Aprobar entrada al grupo
                bot.approve_chat_join_request(chat_id, user_id)
                bot.answer_callback_query(call.id, "¡Verificación Exitosa!", show_alert=True)
                
                bot.edit_message_text(
                    "✅ **¡Verificación completada con éxito!**\n\n"
                    "Ya has sido aprobado para ingresar al grupo.",
                    chat_id=call.message.chat.id,
                    message_id=call.message.message_id,
                    parse_mode="Markdown"
                )
                
                del pending_verifications[user_id]
                
                # Desplegar el menú
                mostrar_menu_bienvenida(bot, call.message.chat.id)

            except Exception as e:
                bot.send_message(call.message.chat.id, f"❌ Ocurrió un error al aprobar tu solicitud: {e}")
        else:
            bot.answer_callback_query(call.id, "❌ Respuesta incorrecta. Inténtalo de nuevo.", show_alert=True)

def mostrar_menu_bienvenida(bot, chat_id):
    """Aquí llamas/construyes tu menú oficial"""
    markup = types.InlineKeyboardMarkup()
    btn_info = types.InlineKeyboardButton("ℹ️ Funciones del Bot", callback_data="bot_info")
    btn_canal = types.InlineKeyboardButton("📢 Canal Oficial", url="https://t.me/COMUNIDV")
    markup.add(btn_info)
    markup.add(btn_canal)

    bot.send_message(
        chat_id,
        "🎉 **¡Bienvenido a la comunidad!**\n\n"
        "Explora nuestros servicios y herramientas oficiales desde este menú:",
        reply_markup=markup,
        parse_mode="Markdown"
  )
  
