from telebot.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

def registrar_calculadora(bot, obtener_cache_func, obtener_teclado_func):
    """
    Registra el módulo de calculadora interactiva de divisas BCV + 0.5%.
    """

    def solicitar_monto_mensaje(message):
        """Entrada desde el teclado de texto '📟 Calculadora'"""
        if message.chat.type != 'private':
            return
        
        # Teclado fijo inferior con un solo botón de escape
        markup = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        markup.add(KeyboardButton("⬅️ Volver al menú"))

        msg = bot.send_message(
            message.chat.id,
            "📟 *CALCULADORA AUTOMÁTICA 📆BCV (+0.5% Intervención)*\n\n"
            "¿Cuántos 💸 USD deseas calcular?\n"
            "Escribe la cifra directamente en el chat (Ejemplo: `5`, `12.5`, `30`, `500`):\n\n"
            "⏳ _Esperando tu monto..._",
            parse_mode="Markdown",
            reply_markup=markup
        )
        bot.register_next_step_handler(msg, procesar_calculo)

    def solicitar_monto_inline(call):
        """Entrada desde el botón inline '🔄 Calcular otro monto'"""
        chat_id = call.message.chat.id

        # Responder al callback para quitar el estado de carga en Telegram
        bot.answer_callback_query(call.id)

        # Teclado fijo inferior por si el usuario decide volver desde aquí
        markup_reply = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        markup_reply.add(KeyboardButton("⬅️ Volver al menú"))

        msg = bot.send_message(
            chat_id,
            "📟 *CALCULADORA AUTOMÁTICA 📆BCV (+0.5% Intervención)*\n\n"
            "¿Cuántos 💸 USD deseas calcular?\n"
            "Escribe la cifra directamente en el chat (Ejemplo: `5`, `12.5`, `30`, `500`):\n\n"
            "⏳ _Esperando tu monto..._",
            parse_mode="Markdown",
            reply_markup=markup_reply
        )
        bot.register_next_step_handler(msg, procesar_calculo)

    def procesar_calculo(message):
        """Procesa la cifra o restablece el menú si decide volver"""
        if message.chat.type != 'private':
            return

        texto = message.text.strip() if message.text else ""

        # Opción de salida: presiona 'Volver al menú' o envía un comando
        if texto == "⬅️ Volver al menú" or texto.startswith("/"):
            teclado_restablecido = obtener_teclado_func(message.from_user)
            bot.send_message(
                message.chat.id,
                "🏡 *Menú principal restablecido.*",
                parse_mode="Markdown",
                reply_markup=teclado_restablecido
            )
            return

        # Normalizar coma a punto decimal (ej: 12,5 -> 12.5)
        texto_limpio = texto.replace(",", ".")
        
        try:
            monto_usd = float(texto_limpio)
            if monto_usd <= 0:
                raise ValueError("Monto positivo requerido")
        except ValueError:
            bot.send_message(
                message.chat.id,
                "⚠️ *Monto inválido.* Por favor escribe solo números (Ejemplo: `15` o `20.5`) "
                "o presiona *⬅️ Volver al menú* abajo.",
                parse_mode="Markdown"
            )
            # Reintentar escuchando el mensaje nuevamente
            bot.register_next_step_handler(message, procesar_calculo)
            return

        # Tasa BCV desde el cache / Redis
        cache = obtener_cache_func()
        tasa_bcv = cache.get("bcv_tasa", 745.64)
        tasa_con_intervencion = tasa_bcv * 1.005  # Tasa + 0.5%
        monto_bolivares = monto_usd * tasa_con_intervencion

        respuesta = (
            f"♻️ *RESULTADO DE CÁLCULO BCV*\n\n"
            f"💵 *Monto en USD:* $`{monto_usd:,.2f}`\n"
            f"🏛️ *Tasa BCV oficial:* `{tasa_bcv:,.2f}` Bs.\n"
            f"⚖️ *Tasa + 0.5% Intervención:* `{tasa_con_intervencion:,.4f}` Bs.\n\n"
            f"💰 *Total a pagar en Bolívares:*\n"
            f"👉 *`{monto_bolivares:,.2f}` Bs.*\n\n"
            f"_Cálculo basado en la tasa oficial del día._"
        )

        # Botón Inline para encadenar múltiples cálculos
        markup_inline = InlineKeyboardMarkup()
        markup_inline.add(InlineKeyboardButton("🔄 Calcular otro monto", callback_data="recalcular_monto"))

        msg_res = bot.send_message(
            message.chat.id,
            respuesta,
            parse_mode="Markdown",
            reply_markup=markup_inline
        )
        
        bot.register_next_step_handler(msg_res, procesar_calculo)

    # Manejador del callback del botón inline
    @bot.callback_query_handler(func=lambda call: call.data == "recalcular_monto")
    def callback_recalcular(call):
        solicitar_monto_inline(call)

    return solicitar_monto_mensaje
    
