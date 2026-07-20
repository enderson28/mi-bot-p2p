import time
import threading

# Configuración del mensaje
ID_GRUPO = "@COMUNIDADAS04"  # Reemplaza con el ID de tu grupo
INTERVALO_HORAS = 6       # Cambia a 12 si prefieres cada 12 horas

TEXTO_ANUNCIO = (
    "🤖 <b>¡Consulta las Tasas y Guías en Privado!</b>\n\n"
    "Para mantener el grupo libre de spam, las herramientas oficiales de "
    "<b>[Comunidad - AntonyS4]</b> están disponibles en chat privado.\n\n"
    "📊 <b>Monitor P2P / BCV en tiempo real</b>\n"
    "💸 <b>Calculadora de Intervención</b>\n"
    "💳 <b>Guías paso a paso (BPay / GPay)</b>\n\n"
    "👉 <b>Toca aquí para iniciar:</b> @BancoIDV_bot"
)

def bucle_anuncios(bot):
    """Bucle infinito que envía el anuncio en segundo plano."""
    # Convertimos horas a segundos (6 horas = 21600 segundos)
    segundos_espera = INTERVALO_HORAS * 3600

    while True:
        try:
            # 1. ESPERA PRIMERO LAS 6 HORAS COMPLETAS
            time.sleep(segundos_espera)
            
            # 2. ENVÍA EL ANUNCIO DESPUÉS DE ESPERAR
            bot.send_message(ID_GRUPO, TEXTO_ANUNCIO, parse_mode="HTML")
            print(f"📢 Anuncio automático enviado con éxito al grupo {ID_GRUPO}")
            
        except Exception as e:
            print(f"⚠️ Error al enviar el anuncio automático: {e}")
            # Si falla (por ejemplo, sin internet), reintenta en 1 minuto
            time.sleep(60)
            

def iniciar_modulo_anuncios(bot):
    """Inicia el hilo secundario para no bloquear el bot principal."""
    hilo = threading.Thread(target=bucle_anuncios, args=(bot,), daemon=True)
    hilo.start()
    print("⏰ Módulo de anuncios automáticos activado correctamente.")
  
