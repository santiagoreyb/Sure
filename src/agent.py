"""Cliente del agente de Azure AI Foundry."""

from __future__ import annotations

import streamlit as st
from azure.ai.projects import AIProjectClient

from src.auth import get_credential
from src.config import CONNECTION_STRING, MONITOR_CONNECTION_STRING
from src.governance import validate_input, validate_output
from src.telemetry import init_telemetry

import logging
logger = logging.getLogger(__name__)

# Inicializar Telemetría una sola vez al cargar el módulo con la cadena específica de Application Insights
if init_telemetry(MONITOR_CONNECTION_STRING):
    logger.info("✅ agent.py: Telemetría inicializada correctamente.")
else:
    logger.warning("⚠️ agent.py: Telemetría no se pudo inicializar. Verifica AZURE_MONITOR_CONNECTION_STRING.")


@st.cache_resource(show_spinner=False)
def get_client() -> AIProjectClient:
    """Crea y cachea una instancia única de AIProjectClient."""
    client = AIProjectClient.from_connection_string(
        credential=get_credential(),
        conn_str=CONNECTION_STRING,
    )
    
    # Habilitar telemetría en el SDK para que use OpenTelemetry configurado en init_telemetry
    try:
        if hasattr(client, 'telemetry'):
            client.telemetry.update(enable=True)
    except Exception:
        pass # Silenciar si el SDK no soporta esta propiedad específica
        
    return client


def create_thread(client: AIProjectClient) -> str:
    """Crea un nuevo hilo de conversación y retorna su ID."""
    return client.agents.create_thread().id


def send_message(
    client: AIProjectClient,
    thread_id: str,
    agent_id: str,
    prompt: str,
) -> dict:
    """Envía un mensaje al agente y retorna la respuesta completa con anotaciones.

    Retorna
    -------
    dict
        ``{"value": "texto de respuesta", "annotations": [...]}``
    """
    # 1. Gobernanza: Validar entrada (incluye enmascaramiento de PII)
    is_valid, reason, masked_prompt = validate_input(prompt)
    if not is_valid:
        return {
            "value": f"⚠️ **Aviso de Gobernanza:** {reason}",
            "annotations": [],
            "governance_violation": True,
            "masked_prompt": masked_prompt
        }

    # 2. Crear el mensaje del usuario (usando el prompt validado)
    client.agents.create_message(
        thread_id=thread_id,
        role="user",
        content=masked_prompt,
    )

    # 2. Ejecutar el agente de forma síncrona
    client.agents.create_and_process_run(
        thread_id=thread_id,
        agent_id=agent_id,
    )

    # 3. Obtener los mensajes más recientes
    api_messages = client.agents.list_messages(thread_id=thread_id)

    for text_msg in api_messages.text_messages:
        data = text_msg.as_dict()
        text_obj = data.get("text", {})
        if isinstance(text_obj, dict):
            raw_value = text_obj.get("value", "")
            # Gobernanza: Validar salida (incluye enmascaramiento de PII)
            cleaned_value, violations = validate_output(raw_value)
            return {
                "value": cleaned_value,
                "annotations": text_obj.get("annotations", []),
                "governance_violations": violations
            }
        
        raw_value = str(text_obj)
        cleaned_value, violations = validate_output(raw_value)
        return {
            "value": cleaned_value, 
            "annotations": [],
            "governance_violations": violations
        }

def get_thread_messages(client: AIProjectClient, thread_id: str) -> list[dict]:
    """Obtiene todos los mensajes de un hilo y los formatea para el estado de Streamlit."""
    api_messages = client.agents.list_messages(thread_id=thread_id)
    formatted_messages = []
    
    # list_messages devuelve los mensajes en orden cronológico inverso (el más reciente primero)
    # Queremos mostrarlos en orden cronológico para el chat
    for msg in reversed(list(api_messages.data)):
        role = msg.role
        content = ""
        for content_part in msg.content:
            if hasattr(content_part, 'text'):
                content += content_part.text.value
            elif isinstance(content_part, dict) and 'text' in content_part:
                content += content_part['text'].get('value', '')
        
        if content:
            formatted_messages.append({
                "role": role,
                "content": content,
                "source": "text" # Asumimos texto por defecto al recargar
            })
            
    return formatted_messages
