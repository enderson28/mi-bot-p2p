import random
from telebot import types

pending_verifications = {}

def registrar_solicitud_pendiente(user_id, chat_id):
    """Guarda la solicitud de ingreso en la memoria temporal del bot."""
    pending_verifications[user_id] = {
        "chat_id": chat_id,
        "status": "pending"
    }

def setup_verification_handlers(bot, target_channel_id=None, funcion_menu=None, funcion_esta_unido=None):

    # 1. Comando /start y /verificar
    @bot.message_handler(commands=['verificar', 'start'])
    def start_verification(message):
        user = message.from_user
        user_id = user.id

        # A. Si el usuario YA ESTÁ UNIDO (Aprobación manual de Admin o ya verificado)
        if funcion_esta_unido and funcion_esta_unido(user_id):
            if user_id in pending_verifications:
                del pending_verifications[user_id]
            
            if funcion_menu:
                funcion_menu(bot, user, message.chat.id)
            return

        # B. Si NO está unido pero TIENE captcha pendiente -> Genera la suma
        if user_id in pending_verifications:
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
            markup.add(*buttons)

            bot.send_message(
                user_id,
                f"🤖 **Verificación de Seguridad**\n\n"
                f"¿Cuánto es **{num1} + {num2}**?\n"
                f"Selecciona el botón correcto para aprobar tu entrada:",
                reply_markup=markup,
                parse_mode="Markdown"
            )
            return

        # C. Si NO está unido y NO tiene captcha pendiente -> Bloqueo genérico
        bot.send_message(
            message.chat.id,
            "⚠️ <b>Acceso Restringido</b>\n\n"
            "Este bot es de uso exclusivo para nuestra comunidad.\n"
            "Solicita tu ingreso a través del enlace oficial del canal.",
            parse_mode="HTML"
        )

    # 2. Callback del Captcha
    @bot.callback_query_handler(func=lambda call: call.data.startswith("captcha_"))
    def process_captcha(call):
        user = call.from_user
        user_id = user.id
        user_answer = call.data.split("_")[1]

        if user_id not in pending_verifications:
            bot.answer_callback_query(call.id, "No tienes ninguna verificación pendiente.")
            return

        expected_answer = pending_verifications[user_id].get("answer")
        chat_id = pending_verifications[user_id].get("chat_id")

        if user_answer == expected_answer:
            try:
                # Intenta aprobar la solicitud en Telegram
                try:
                    bot.approve_chat_join_request(chat_id, user_id)
                except Exception as e:
                    print(f"Nota: La solicitud ya estaba aprobada o expiró: {e}")

                bot.answer_callback_query(call.id, "¡Verificación Exitosa!", show_alert=True)
                
                bot.edit_message_text(
                    "✅ **¡Verificación completada con éxito!**\n\n"
                    "Ya has sido aprobado para ingresar a la comunidad.",
                    chat_id=call.message.chat.id,
                    message_id=call.message.message_id,
                    parse_mode="Markdown"
                )
                
                # Eliminamos de pendientes
                if user_id in pending_verifications:
                    del pending_verifications[user_id]
                
                # Desplegamos el menú oficial correspondiente (8 o 5 botones)
                if funcion_menu:
                    funcion_menu(bot, user, call.message.chat.id)

            except Exception as e:
                bot.send_message(call.message.chat.id, f"❌ Ocurrió un error al procesar tu verificación: {e}")
        else:
            bot.answer_callback_query(call.id, "❌ Respuesta incorrecta. Inténtalo de nuevo.", show_alert=True)
            
