import os
import requests
from telebot.types import ReplyKeyboardMarkup, KeyboardButton

# Modelo por defecto en OpenRouter (puedes cambiarlo si deseas)
MODELO_IA = "openai/gpt-3.5-turbo"

def registrar_ia_consulta(bot, obtener_cache_func, obtener_teclado_func):
    """
    Registra el módulo interactivo de consulta financiera con IA vía OpenRouter.
    """

    def solicitar_consulta_ia(message):
        """Punto de entrada al presionar el botón del menú"""
        if message.chat.type != 'private':
            return

        # Teclado aislado de escape exclusivo para este flujo
        markup = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        markup.add(KeyboardButton("⬅️ Salir al menú"))

        msg = bot.send_message(
            message.chat.id,
            "🤖 **CONSULTA CON IA FINANCIERA**\n\n"
            "Escribe tu duda o consulta en el chat (Ejemplo: *¿Cuál es el margen de arbitraje hoy?* o *¿Cómo impacta la tasa BCV en P2P?*):\n\n"
            "⏳ *Esperando tu consulta...*",
            parse_mode="Markdown",
            reply_markup=markup
        )
        
        # Siguiente paso en la conversación
        bot.register_next_step_handler(msg, procesar_consulta_ia)


    def procesar_consulta_ia(message):
        """Procesa la pregunta del usuario con la API de OpenRouter o sale al menú"""
        if message.chat.type != 'private':
            return

        texto = message.text.strip() if message.text else ""

        # Opción de salida al presionar el botón dedicado
        if texto == "⬅️ Salir al menú" or texto.startswith("/"):
            teclado_restablecido = obtener_teclado_func(message.from_user)
            bot.send_message(
                message.chat.id,
                "💡 *Menú principal restablecido.*",
                parse_mode="Markdown",
                reply_markup=teclado_restablecido
            )
            return

        # Notificación visual de pensamiento
        msg_espera = bot.send_message(message.chat.id, "🧠 *Analizando respuesta...*", parse_mode="Markdown")

        # Obtener contexto de tasas en tiempo real desde Redis / Cache
        cache = obtener_cache_func()
        tasa_bcv = cache.get("bcv_tasa", "No disponible")

        # Llamada a la API de OpenRouter
        api_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            bot.delete_message(message.chat.id, msg_espera.message_id)
            bot.send_message(message.chat.id, "❌ Error: La API Key de OpenRouter no está configurada en el servidor.")
            return

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

        # Prompt del sistema para contextuar a la IA
        system_prompt = (
            "Eres un asistente virtual experto en arbitraje de criptomonedas, mercado P2P y tasas BCV en Venezuela. "
            f"Contexto actual: La tasa oficial del BCV es {tasa_bcv} VES/USD. "
            "Responde de forma breve, concisa, profesional y fácil de leer para Telegram."
        )

        payload = {
            "model": MODELO_IA,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": texto}
            ]
        }

        try:
            response = requests.post("https://openrouter.ai/api/v1/chat/completions", json=payload, headers=headers, timeout=15)
            data = response.json()

            if response.status_code == 200 and "choices" in data:
                respuesta_ia = data["choices"][0]["message"]["content"]
            else:
                respuesta_ia = "⚠️ Ocurrió un inconveniente al procesar la respuesta con la IA. Intenta de nuevo."
        except Exception as e:
            respuesta_ia = "⚠️ Error de conexión con el servicio de IA."

        # Borramos el mensaje de "Analizando..."
        try:
            bot.delete_message(message.chat.id, msg_espera.message_id)
        except Exception:
            pass

        # Mostramos la respuesta y mantenemos el botón para seguir consultando
        markup_continuar = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        markup_continuar.add(KeyboardButton("⬅️ Salir al menú"))

        msg_res = bot.send_message(
            message.chat.id,
            f"🤖 **Respuesta:**\n\n{respuesta_ia}",
            parse_mode="Markdown",
            reply_markup=markup_continuar
        )

        # Mantiene la conversación abierta escuchando el siguiente mensaje
        bot.register_next_step_handler(msg_res, procesar_consulta_ia)

    return solicitar_consulta_ia
      
