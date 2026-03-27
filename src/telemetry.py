"""Módulo para la configuración de monitoreo y tracing con OpenTelemetry."""

import logging
from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from azure.monitor.opentelemetry.exporter import AzureMonitorTraceExporter

# Configuración de logging básico para telemetría
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def init_telemetry(connection_string: str) -> bool:
    """
    Inicializa el stack de OpenTelemetry para enviar trazas a Azure Monitor.

    Args:
        connection_string: Cadena de conexión de Application Insights.

    Returns:
        bool: True si se inicializó correctamente, False en caso contrario.
    """
    if not connection_string:
        logger.warning("⚠️ Telemetría: No se proporcionó AZURE_MONITOR_CONNECTION_STRING. Tracing deshabilitado.")
        return False

    if not any(k in connection_string for k in ["InstrumentationKey=", "IngestionEndpoint=", "ConnectionString="]):
        logger.warning(
            "⚠️ Telemetría: CONNECTION_STRING de monitorización parece incorrecta. "
            "Debe ser la cadena de Application Insights (InstrumentationKey o ConnectionString)."
        )
        return False

    try:
        resource = Resource.create({"service.name": "sure-agent"})
        provider = TracerProvider(resource=resource)
        trace.set_tracer_provider(provider)

        exporter = AzureMonitorTraceExporter.from_connection_string(connection_string)
        span_processor = BatchSpanProcessor(exporter)
        provider.add_span_processor(span_processor)

        logger.info("🚀 Telemetría: Tracing habilitado hacia Azure Monitor.")
        return True

    except Exception as e:
        logger.error(f"❌ Telemetría: Error al inicializar el exportador: {e}")
        return False


def get_tracer(name: str):
    """Obtiene un tracer para instrumentación manual si es necesario."""
    return trace.get_tracer(name)
