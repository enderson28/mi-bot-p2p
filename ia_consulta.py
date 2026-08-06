import os
import json
import requests
from datetime import datetime, timedelta
from telebot.types import ReplyKeyboardMarkup, KeyboardButton

# Modelo en OpenRouter con mayor nivel de razonamiento y ultra económico
MODELO_IA = "openai/gpt-4o-mini"

# ID DEL CREADOR / ADMINISTRADORES (Sin límites ni restricciones)
ADMIN_IDS = [5073264705, 1676933074]

# Diccionarios globales en memoria
HISTORIAL_CHAT = {}
# Estructura: {user_id: {"fecha": "YYYY-MM-DD", "preguntas": int}}
USO_DIARIO_USUARIOS = {}
# Registro del cupo global: {"fecha": "", "usuarios_registrados": set(user_ids)}
REGISTRO_CUPO_DIARIO = {"fecha": "", "usuarios_registrados": set()}

# Definición de canales en la parte superior
CANAL_PRUEBA = "@COMUNIDV"
CANAL_CONGESTIONADO = "@COMUNIDADAS04"


def registrar_ia_consulta(bot, redis_client, obtener_teclado_func):

    # 🔒 VERIFICACIÓN MULTI-CANAL
    def usuario_esta_unido(user_id):
        if user_id in ADMIN_IDS:
            return True

        # 1. Probar en el canal de pruebas
        try:
            m1 = bot.get_chat_member(CANAL_PRUEBA, user_id)
            if m1.status in ['creator', 'administrator', 'member']:
                return True
        except Exception:
            pass  # Si el bot no está en el canal o falla, pasa al siguiente

        # 2. Probar en el canal principal / congestionado
        try:
            m2 = bot.get_chat_member(CANAL_CONGESTIONADO, user_id)
            if m2.status in ['creator', 'administrator', 'member']:
                return True
        except Exception:
            pass

        return False

    # DICCIONARIO DE EMOJIS ANIMADOS DE TELEGRAM (IDs)
    TG_EMOJIS = {
        "BANCO": "5183805009766123191",       # 🏦 (BCV)
        "PROHIBIDO": "5260293700088511294",   # ⛔
        "RELOJ_ARENA": "5447644880824181073", # ⏳
        "SIRENA": "5395695537687123235",      # 🚨
        "ESTADISTICA": "5231200819986047254", # 📊
        "ESCUDO": "5197288647275071607",      # 🛡️
        "VISTO": "5206607081334906820",       # ✔️
        "MEGAFONO": "5424818078833715060",    # 📣
        "BOMBILLA": "5422439311196834318",    # 💡
        "ROBOT": "5323772371830588991",       # 🤖
        "FLECHA_ABAJO": "5406745015365943482",# ⬇️
        "RAYO": "5456140674028019486",        # ⚡
        "CONSULTAR": "5303130782004924588"    # 💬
    }

    def e(key, fallback=""):
        emoji_id = TG_EMOJIS.get(key, "")
        if emoji_id:
            return f'<tg-emoji emoji-id="{emoji_id}">{fallback}</tg-emoji>'
        return fallback

    # ------------------------------------------------------------------
    # HANDLER PARA EL COMANDO /ia (EXCLUSIVO CREADOR / ADMINS)
    # ------------------------------------------------------------------
    @bot.message_handler(commands=['ia'])
    def publicar_anuncio_ia(message):
        user_id = message.from_user.id
        if user_id not in ADMIN_IDS:
            return

        bot_info = bot.get_me()
        bot_link = f"https://t.me/{bot_info.username}"

        anuncio = (
            f"{e('ROBOT', '🤖')} <blockquote><b>SERVICIO DE CONSULTA IA FINANCIERA</b></blockquote> {e('ROBOT', '🤖')}\n\n"
            f"{e('MEGAFONO', '📣')} <i>Estimada comunidad, para mantener este servicio gratuito, rápido y sostenible, "
            f"el módulo de IA opera bajo los siguientes parámetros en privado:</i>\n\n"
            f"{e('VISTO', '✔️')} <b>Cupo Global:</b> 100 usuarios diarios.\n"
            f"{e('PROHIBIDO', '⛔')} <b>Límite Individual:</b> 30 consultas por usuario en su día de acceso.\n"
            f"{e('FLECHA_ABAJO', '⬇️')} <b>Rotación Equitativa:</b> Si usas la IA hoy, se activará un día de descanso para ti mañana, "
            f"permitiendo que otros miembros del canal puedan consultar.\n"
            f"{e('BANCO', '🏦')} <b>Actualización:</b> Datos en tiempo real de la tasa oficial del BCV.\n\n"
            f"{e('RAYO', '⚡')} <i>¡Ingresa al bot en privado en <a href='{bot_link}'>@{bot_info.username}</a> y presiona el botón 🤖 <b>IA Consulta</b> para iniciar!</i>"
        )

        bot.send_message(
            message.chat.id,
            anuncio,
            parse_mode="HTML",
            disable_web_page_preview=True
        )

    # ------------------------------------------------------------------
    # FLUJO EN PRIVADO
    # ------------------------------------------------------------------
    def solicitar_consulta_ia(message):
        if message.chat.type != "private":
            return

        user_id = message.from_user.id
        chat_id = message.chat.id

        # --- Acceso Restringido (No unido al canal) ---
        if not usuario_esta_unido(user_id):
            bot.send_message(
                chat_id,
                f"{e('ESCUDO', '🛡️')} <b>Acceso Restringido</b>\n\n"
                f"Para utilizar el módulo de IA Consulta debes ser miembro de nuestra comunidad oficial:\n"
                f"👉 <b>{CANAL_CONGESTIONADO}</b>\n\n"
                f"<i>Una vez te hayas unido, vuelve a presionar el botón.</i>",
                parse_mode="HTML"
            )
            return

        HISTORIAL_CHAT[chat_id] = []

        markup = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        markup.add(KeyboardButton("⬅️ Salir al menú"))

        msg = bot.send_message(
            chat_id,
            f"{e('ROBOT', '🤖')} <b>CONSULTA CON IA FINANCIERA</b>\n\n"
            "Haz tus preguntas sobre el mercado P2P, arbitraje, tasas y estrategias.\n\n"
            f"{e('RELOJ_ARENA', '⏳')} <i>Esperando tu consulta...</i>",
            parse_mode="HTML",
            reply_markup=markup
        )
        bot.register_next_step_handler(msg, procesar_consulta_ia)

    def procesar_consulta_ia(message):
        if message.chat.type != "private":
            return

        user_id = message.from_user.id

        if not usuario_esta_unido(user_id):
            bot.send_message(
                message.chat.id,
                f"{e('PROHIBIDO', '⛔')} <b>Acceso Denegado</b>\n\n"
                f"Debes unirte a nuestra comunidad oficial <b>{CANAL_CONGESTIONADO}</b> para continuar utilizando la IA.",
                parse_mode="HTML"
            )
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
                f"{e('BOMBILLA', '💡')} <b>Menú principal restablecido.</b>",
                parse_mode="HTML",
                reply_markup=teclado_restablecido
            )
            return

        # CONTROL DE ACCESO, CUPO Y DÍA INTERMEDIO (Solo si NO es Admin)
        fecha_hoy_dt = datetime.now()
        fecha_hoy = fecha_hoy_dt.strftime("%Y-%m-%d")
        fecha_ayer = (fecha_hoy_dt - timedelta(days=1)).strftime("%Y-%m-%d")

        if user_id not in ADMIN_IDS:
            # 1. Resetear el registro global si es un nuevo día
            if REGISTRO_CUPO_DIARIO["fecha"] != fecha_hoy:
                REGISTRO_CUPO_DIARIO["fecha"] = fecha_hoy
                REGISTRO_CUPO_DIARIO["usuarios_registrados"] = set()

            # 2. Control de Día Intermedio (Cooldown de 24h)
            if user_id in USO_DIARIO_USUARIOS:
                ultima_fecha_uso = USO_DIARIO_USUARIOS[user_id].get("fecha")
                if ultima_fecha_uso == fecha_ayer:
                    bot.send_message(
                        chat_id,
                        f"{e('FLECHA_ABAJO', '⬇️')} <b>Día de rotación activo</b>\n\n"
                        f"Ayer utilizaste el módulo de IA. Para permitir que otros miembros de la comunidad puedan consultar, hoy es tu día de descanso.\n\n"
                        f"{e('CONSULTAR', '💬')} <i>Podrás volver a consultar mañana.</i>",
                        parse_mode="HTML"
                    )
                    bot.register_next_step_handler(message, procesar_consulta_ia)
                    return

            # 3. Control del Cupo Global (Máximo 100 usuarios por día)
            if user_id not in REGISTRO_CUPO_DIARIO["usuarios_registrados"]:
                if len(REGISTRO_CUPO_DIARIO["usuarios_registrados"]) >= 100:
                    bot.send_message(
                        chat_id,
                        f"{e('PROHIBIDO', '⛔')} <b>Cupo diario alcanzado</b>\n\n"
                        f"Los 100 cupos diarios para consultas de IA ya han sido tomados hoy por otros usuarios.\n\n"
                        f"🌅 <i>Por favor, intenta nuevamente mañana a primera hora.</i>",
                        parse_mode="HTML"
                    )
                    bot.register_next_step_handler(message, procesar_consulta_ia)
                    return
                else:
                    REGISTRO_CUPO_DIARIO["usuarios_registrados"].add(user_id)

            # 4. Inicializar o Resetear contador individual si es un nuevo día
            if user_id not in USO_DIARIO_USUARIOS or USO_DIARIO_USUARIOS[user_id]["fecha"] != fecha_hoy:
                USO_DIARIO_USUARIOS[user_id] = {"fecha": fecha_hoy, "preguntas": 0}

            # 5. Verificar Límite Individual de 30 Preguntas
            if USO_DIARIO_USUARIOS[user_id]["preguntas"] >= 30:
                bot.send_message(
                    chat_id,
                    f"{e('SIRENA', '🚨')} <b>Has alcanzado el límite diario de 30 consultas</b>\n\n"
                    f"Por favor, regresa pasado mañana para continuar o utiliza las herramientas del menú.",
                    parse_mode="HTML"
                )
                bot.register_next_step_handler(message, procesar_consulta_ia)
                return

            # Incrementar contador si pasa todas las validaciones
            USO_DIARIO_USUARIOS[user_id]["preguntas"] += 1
            preguntas_usadas = USO_DIARIO_USUARIOS[user_id]["preguntas"]
        else:
            preguntas_usadas = 0

        # Notificación visual
        msg_espera = bot.send_message(
            chat_id,
            f"{e('ROBOT', '🧠')} <b>Analizando respuesta...</b>",
            parse_mode="HTML"
        )

        # OBTENER BCV TASA DESDE REDIS
        tasa_bcv = "No disponible"
        if redis_client:
            try:
                data_raw = redis_client.get("CACHE_TASAS_STORAGE")
                if data_raw:
                    dato = json.loads(data_raw) if isinstance(data_raw, str) else json.loads(data_raw.decode('utf-8'))
                    tasa_bcv = dato.get("bcv_tasa", "No disponible")
            except Exception as err:
                print(f"Error extrayendo tasa de Redis: {err}")

        # CONFIGURACIÓN DE PROMPT Y OPTIMIZACIÓN
        system_prompt = (
            f"Eres un asistente financiero y analista experto en arbitraje de criptomonedas y mercado P2P en Venezuela. "
            f"DATOS EN TIEMPO REAL: La tasa oficial BCV actual registrada en el sistema es: {tasa_bcv} Bs/USD. "
            f"INSTRUCCIONES DE RESPUESTA: Sé extremadamente directo, conciso y natural. "
            f"REGLA MATEMÁTICA OBLIGATORIA: Si realizas cálculos numéricos o porcentuales, verifica la precisión matemática. "
            f"REGLA DE BREVEDAD: Responde en máximo 2 o 3 párrafos cortos (alrededor de 8 a 10 líneas en total). "
            f"REGLA PARA PREGUNTAS GENERALES: Si la duda del usuario es muy vaga o corta (por ejemplo: 'binance p2p'), da una explicación general."
        )

        if chat_id not in HISTORIAL_CHAT:
            HISTORIAL_CHAT[chat_id] = []

        HISTORIAL_CHAT[chat_id].append({"role": "user", "content": texto})

        # OPTIMIZACIÓN: Enviamos solo los últimos 8 mensajes
        historial_reciente = HISTORIAL_CHAT[chat_id][-8:]
        messages_payload = [{"role": "system", "content": system_prompt}] + historial_reciente

        payload = {
            "model": MODELO_IA,
            "messages": messages_payload,
            "max_tokens": 500,
            "temperature": 0.3
        }

        openrouter_key = os.getenv("OPENROUTER_API_KEY")
        headers = {
            "Authorization": f"Bearer {openrouter_key}",
            "Content-Type": "application/json"
        }

        try:
            response = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                json=payload,
                headers=headers,
                timeout=20
            )
            data = response.json()

            if response.status_code == 200 and "choices" in data:
                respuesta_ia = data["choices"][0]["message"]["content"]
                HISTORIAL_CHAT[chat_id].append({"role": "assistant", "content": respuesta_ia})

                # Pie de página dinámico con emojis (solo si la consulta fue exitosa)
                if user_id not in ADMIN_IDS:
                    restantes = 30 - preguntas_usadas
                    pie_pagina = (
                        f"\n\n---\n"
                        f"{e('ESTADISTICA', '📊')} <b>Uso diario:</b> <code>{preguntas_usadas}/30</code> consultas | "
                        f"{e('RAYO', '⚡')} <b>Restantes hoy:</b> <code>{restantes}</code>"
                    )
                    respuesta_ia += pie_pagina
            else:
                print(f"⚠️ Error OpenRouter [{response.status_code}]: {data}")
                respuesta_ia = f"{e('RELOJ_ARENA', '⚠️')} <b>Ocurrió un inconveniente al obtener la respuesta del modelo de IA.</b>"

        except Exception as err:
            print(f"⚠️ Excepción HTTP: {err}")
            respuesta_ia = f"{e('RELOJ_ARENA', '⚠️')} <b>Error de conexión con el servicio de IA.</b>"

        # Borrar mensaje "Analizando..." y enviar respuesta final
        try:
            bot.delete_message(chat_id, msg_espera.message_id)
        except Exception:
            pass

        bot.send_message(
            chat_id,
            f"{e('ROBOT', '🤖')} <b>Respuesta:</b>\n\n{respuesta_ia}",
            parse_mode="HTML"
        )

        # Seguir escuchando para mantener la conversación
        bot.register_next_step_handler_by_chat_id(chat_id, procesar_consulta_ia)

    return solicitar_consulta_ia
                    
