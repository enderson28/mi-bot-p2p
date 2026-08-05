import os
import requests
from telebot.types import ReplyKeyboardMarkup, KeyboardButton

# Modelo en OpenRouter con mayor nivel de razonamiento y ultra económico
MODELO_IA = "openai/gpt-4o-mini"

# Diccionario global para mantener el historial de chat por usuario en memoria
HISTORIAL_CHAT = {}

def registrar_ia_consulta(bot, redis_client, obtener_teclado_func):
    """
    Registra el módulo interactivo de consulta financiera con IA vía OpenRouter.
    Mantiene el hilo conversacional e inyecta datos de Redis.
    """

    def solicitar_consulta_ia(message):
        """Punto de entrada al presionar el botón del menú"""
        if message.chat.type != 'private':
            return

        chat_id = message.chat.id
        # Limpiamos historial previo al iniciar una nueva sesión
        HISTORIAL_CHAT[chat_id] = []

        markup = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        markup.add(KeyboardButton("⬅️ Salir al menú"))

        msg = bot.send_message(
            chat_id,
            "🤖 **CONSULTA CON IA FINANCIERA**\n\n"
            "Haz tus preguntas sobre el mercado P2P, arbitraje, tasas y estrategias.\n\n"
            "⏳ *Esperando tu consulta...*",
            parse_mode="Markdown",
            reply_markup=markup
        )
        
        bot.register_next_step_handler(msg, procesar_consulta_ia)


    def procesar_consulta_ia(message):
        """Procesa las preguntas manteniendo el historial de conversación"""
        if message.chat.type != 'private':
            return

        chat_id = message.chat.id
        texto = message.text.strip() if message.text else ""

        # Opción de salida
        if texto == "⬅️ Salir al menú" or texto.startswith("/"):
            if chat_id in HISTORIAL_CHAT:
                del HISTORIAL_CHAT[chat_id]

            teclado_restablecido = obtener_teclado_func(message.from_user)
            bot.send_message(
                chat_id,
                "💡 *Menú principal restablecido.*",
                parse_mode="Markdown",
                reply_markup=teclado_restablecido
            )
            return

        # Notificación visual
        msg_espera = bot.send_message(chat_id, "🧠 *Analizando respuesta...*", parse_mode="Markdown")

        # Obtener valores de Redis comprobando posibles nombres de claves
        tasa_bcv = "No disponible"
        if redis_client:
            try:
                # Intenta obtener según los nombres habituales en tus scripts
                val = (redis_client.get("bcv_tasa") or 
                       redis_client.get("tasa_bcv") or 
                       redis_client.get("bcv") or 
                       redis_client.get("precio_bcv"))
                if val:
                    tasa_bcv = val.decode('utf-8') if isinstance(val, bytes) else str(val)
            except Exception as e:
                print(f"Error leyendo Redis: {e}")

        api_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            try:
                bot.delete_message(chat_id, msg_espera.message_id)
            except Exception:
                pass
            bot.send_message(chat_id, "❌ Error: La API Key de OpenRouter no está configurada en el servidor.")
            return

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

        system_prompt = (
            "Eres un asistente financiero y analista experto en arbitraje de criptomonedas y mercado P2P en Venezuela. "
            f"DATOS EN TIEMPO REAL: La tasa oficial BCV registrada es: {tasa_bcv} VES/USD. "
            "INSTRUCCIONES DE RESPUESTA: Se extremadamente conciso, directo y conversacional. "
            "Responde en máximo 2 o 3 párrafos breves o puntos clave. Evita introducciones largas o explicaciones teóricas innecesarias."
        )
        
        # Recuperar o inicializar historial
        if chat_id not in HISTORIAL_CHAT:
            HISTORIAL_CHAT[chat_id] = []

        # Agregar el mensaje actual del usuario al historial
        HISTORIAL_CHAT[chat_id].append({"role": "user", "content": texto})

        # Limitar el historial a los últimos 10 mensajes para ahorrar tokens y mantener relevancia
        if len(HISTORIAL_CHAT[chat_id]) > 10:
            HISTORIAL_CHAT[chat_id] = HISTORIAL_CHAT[chat_id][-10:]

        messages_payload = [{"role": "system", "content": system_prompt}] + HISTORIAL_CHAT[chat_id]

        payload = {
            "model": MODELO_IA,
            "messages": messages_payload
            "max_tokens": 300,
            "temperature": 0.5
        }

        try:
            response = requests.post("https://openrouter.ai/api/v1/chat/completions", json=payload, headers=headers, timeout=20)
            data = response.json()

            if response.status_code == 200 and "choices" in data:
                respuesta_ia = data["choices"][0]["message"]["content"]
                # Guardamos la respuesta de la IA en el historial
                HISTORIAL_CHAT[chat_id].append({"role": "assistant", "content": respuesta_ia})
            else:
                # Imprime el motivo exacto en los Deploy Logs de Railway si falla:
                print(f"⚠️ Error OpenRouter [{response.status_code}]: {data}")
                respuesta_ia = "⚠️ Ocurrió un inconveniente al obtener la respuesta del modelo de IA."
        except Exception as e:
            print(f"⚠️ Excepción HTTP: {e}")
            respuesta_ia = "⚠️ Error de conexión con el servicio de IA."

        # Borrar mensaje de espera
        try:
            bot.delete_message(chat_id, msg_espera.message_id)
        except Exception:
            pass

        markup_continuar = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        markup_continuar.add(KeyboardButton("⬅️ Salir al menú"))

        msg_res = bot.send_message(
            chat_id,
            f"🤖 **Respuesta:**\n\n{respuesta_ia}",
            parse_mode="Markdown",
            reply_markup=markup_continuar
        )

        # Permite continuar la conversación en bucle
        bot.register_next_step_handler(msg_res, procesar_consulta_ia)

    return solicitar_consulta_ia
        
