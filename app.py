"""Sure Agent – Interfaz de Chat con Streamlit."""

import time
import streamlit as st

from src.agent import get_client, create_thread, send_message, get_thread_messages
from src.citations import process_citations
from src.governance import validate_input
from src.config import AGENT_ID, SPEECH_KEY, SPEECH_REGION
from src.components.voice import realtime_voice
from src.history import save_thread, load_history
from src.pii import mask_pii

# ── Configuración de página ──────────────────────────────
st.set_page_config(
    page_title="Sure Agent",
    page_icon="🛡️",
    layout="centered",
)

# ── Barra lateral ────────────────────────────────────────
with st.sidebar:
    # 1. MEJORA: Carga de logo local con manejo de errores
    try:
        # Esto hace que el logo se expanda para llenar la barra lateral
        st.image("logo.png", use_container_width=True)
    except FileNotFoundError:
        st.warning("⚠️ Logo no encontrado. Verifica la ruta del archivo.")
        
    st.title("Sure Agent")
    st.caption("Asistente de análisis técnico **SURE** para reclamos bancarios. Evalúa consultas de Cuentas, Tarjetas y Préstamos fundamentándose exclusivamente en documentación contractual indexada para el equipo de cumplimiento.")
    st.divider()
    
    # 2. MEJORA: Botón primario y borrado total del estado
    if st.button("🗑️ Nueva conversación", use_container_width=True, type="primary"):
        st.session_state.clear() # Borra todo de forma más segura
        st.rerun()

    # Nuevo botón para ver el historial
    if st.button("📜 Ver historial", use_container_width=True):
        st.session_state.show_history = not st.session_state.get("show_history", False)
        st.rerun()

    if st.session_state.get("show_history", False):
        st.divider()
        st.subheader("Conversaciones pasadas")
        history = load_history()
        if not history:
            st.caption("No hay conversaciones previas.")
        else:
            for item in history:
                # Mostrar botón con el título y la fecha (opcional acortada)
                if st.button(f"🕒 {item['title']}", key=item['thread_id'], use_container_width=True):
                    with st.spinner("Cargando conversación..."):
                        client = get_client()
                        st.session_state.messages = get_thread_messages(client, item['thread_id'])
                        st.session_state.thread_id = item['thread_id']
                        st.session_state.show_history = False
                    st.rerun()

    st.divider()
    st.caption("🛡️ **Declaración de IA**: SURE es una inteligencia artificial y puede cometer errores. Verifica siempre la información importante.")

# ── Cliente e hilo de conversación ───────────────────────
client = get_client()

if "messages" not in st.session_state:
    st.session_state.messages = []

if "thread_id" not in st.session_state:
    st.session_state.thread_id = create_thread(client)

thread_id = st.session_state.thread_id

# ── Helpers de streaming ─────────────────────────────────
def transmitir_texto(texto: str):
    """Genera texto palabra por palabra para crear efecto de escritura."""
    palabras = texto.split(" ")
    for i, palabra in enumerate(palabras):
        yield palabra + ("" if i == len(palabras) - 1 else " ")
        time.sleep(0.015) # 3. MEJORA: Reduje el tiempo para que la lectura sea más fluida

# ── Pantalla de bienvenida ───────────────────────────────
# 4. MEJORA: Mensaje inicial si el chat está vacío para no mostrar pantalla en blanco
if not st.session_state.messages:
    st.info("👋 **¡Hola! Soy SURE.**\n¿En qué te puedo ayudar hoy?")

# ── Renderizar historial de chat ─────────────────────────
for msg in st.session_state.messages:
    # 5. MEJORA: Avatares personalizados visuales
    avatar_icon = "🛡️" if msg["role"] == "assistant" else "👤"
    
    with st.chat_message(msg["role"], avatar=avatar_icon):
        st.markdown(msg["content"])
        
        if msg.get("fuentes"):
            with st.expander("📚 Ver documentos fuente"):
                for fuente in msg["fuentes"]:
                    st.caption(f"- {fuente}")

# ── Entrada del chat ─────────────────────────────────────

# Determinar si hay un texto del asistente recién generado para hablar
text_to_speak = ""
if st.session_state.messages and st.session_state.messages[-1]["role"] == "assistant":
    # Solo hablar si la fuente de la conversación fue por audio
    if st.session_state.messages[-1].get("source") == "audio":
        text_to_speak = st.session_state.messages[-1]["content"]

# Inicializar estado de voz si no existe
if "voice_active" not in st.session_state:
    st.session_state.voice_active = False

if "show_voice_ui" not in st.session_state:
    st.session_state.show_voice_ui = False

# Renderizar el componente de voz SOLO si la UI está activada
voice_data = None
show_voice_btn = None

if st.session_state.show_voice_ui:
    voice_data = realtime_voice(
        speech_key=SPEECH_KEY,
        speech_region=SPEECH_REGION,
        text_to_speak=text_to_speak,
        is_active=st.session_state.voice_active,
        key="realtime_voice_component"
    )
    st.markdown("<br>", unsafe_allow_html=True)

# Actualizar el estado de activación basado en lo que diga el componente
if voice_data and isinstance(voice_data, dict):
    if "active" in voice_data:
        st.session_state.voice_active = voice_data["active"]

# Extraer el prompt si vino desde voz y es uno nuevo
voice_prompt = None
if voice_data and isinstance(voice_data, dict) and "text" in voice_data:
    if "last_voice_timestamp" not in st.session_state:
        st.session_state.last_voice_timestamp = 0
        
    current_timestamp = voice_data.get("timestamp", 0)
    if current_timestamp > st.session_state.last_voice_timestamp:
        st.session_state.last_voice_timestamp = current_timestamp
        voice_prompt = voice_data["text"]

# ── Línea de entrada con Toggle de Voz ───────────────────
# Ponemos el botón de toggle justo encima del input, alineado a la derecha
tgl_cols = st.columns([0.92, 0.08])
with tgl_cols[1]:
    voice_icon = "🎙️" if st.session_state.show_voice_ui else "🔇"
    if st.button(voice_icon, help="Mostrar/Ocultar controles de voz", key="main_voice_toggle"):
        st.session_state.show_voice_ui = not st.session_state.show_voice_ui
        if st.session_state.show_voice_ui:
            st.toast("⚠️ Chat deshabilitado (Modo Voz activo). Toca 🎙️ para volver a escribir.", icon="🎙️")
        else:
            st.session_state.voice_active = False
        st.rerun()

# El input vuelve a su posición original (Full-width y fijado abajo)
prompt_placeholder = "Escribe tu consulta aquí…" if not st.session_state.show_voice_ui else "Chat deshabilitado (Modo Voz activo)"
prompt = st.chat_input(placeholder=prompt_placeholder)


# Check if we should use the typed prompt or the spoken one
if voice_prompt:
    final_prompt = voice_prompt
    prompt_source = "audio"
elif prompt:
    if st.session_state.show_voice_ui:
        st.toast("⚠️ Debes deshabilitar la interfaz de voz (botón 🎙️) para enviar mensajes de texto", icon="🎙️")
        final_prompt = None
        prompt_source = None
    else:
        final_prompt = prompt
        prompt_source = "text"
        # Si lo escribió por chat pero menciona que lo lea, lo forzamos a hablar
        texto_min = final_prompt.lower()
        if any(p in texto_min for p in ["lee ", "leer", "voz", "audio", "habla", "dilo"]):
            prompt_source = "audio"
else:
    final_prompt = None
    prompt_source = None

# ── Enmascaramiento de PII (Datos Sensibles) ──────────────
if final_prompt:
    # Gobernanza: Validar entrada y enmascarar PII antes de mostrar en el chat
    is_valid, reason, final_prompt = validate_input(final_prompt)

if final_prompt:
    # Si es el primer mensaje, guardamos el hilo en el historial
    if not st.session_state.messages:
        save_thread(st.session_state.thread_id, final_prompt)

    st.session_state.messages.append({"role": "user", "content": final_prompt, "source": prompt_source})
    with st.chat_message("user", avatar="👤"):
        st.markdown(final_prompt)

    with st.chat_message("assistant", avatar="🛡️"):
        fuentes_extraidas = [] 
        try:
            with st.spinner("Analizando documentos técnicos..."):
                resultado = send_message(client, thread_id, AGENT_ID, final_prompt)
                
                if resultado.get("governance_violation"):
                    respuesta = resultado["value"]
                else:
                    respuesta = process_citations(
                        resultado["value"],
                        resultado["annotations"],
                        client,
                    )

            st.write_stream(transmitir_texto(respuesta))
            
            if resultado.get("annotations"):
                with st.expander("📚 Ver documentos fuente"):
                    for anotacion in resultado["annotations"]:
                        texto_cita = getattr(anotacion, 'text', str(anotacion)) 
                        st.caption(f"- {texto_cita}")
                        fuentes_extraidas.append(texto_cita)

            # Guardar el mensaje exitoso en el historial con su fuente
            st.session_state.messages.append(
                {"role": "assistant", "content": respuesta, "fuentes": fuentes_extraidas, "source": prompt_source}
            )
            
            # Re-ejecutar para que el componente de voz lea la nueva respuesta
            st.rerun()

        except Exception as exc:
            # 6. MEJORA: UI de error más amigable sin guardarlo en el historial permanente
            st.error("Ocurrió un error al procesar la solicitud.")
            with st.expander("Detalles del error técnico"):
                st.code(exc, language="python")
