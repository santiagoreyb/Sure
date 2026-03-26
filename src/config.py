"""Configuración centralizada desde variables de entorno."""

import os
from dotenv import load_dotenv

load_dotenv()

CONNECTION_STRING: str = os.getenv(
    "AZURE_AI_CONNECTION_STRING",
    "eastus2.api.azureml.ms;4678cfb9-ccc2-48a0-a15c-92fe77d9ed9d;rg-sure;sure",
)

AGENT_ID: str = os.getenv("AZURE_AI_AGENT_ID", "asst_jxF6c8rPEyErfVcdTdjcMsvI")

TENANT_ID: str = os.getenv("AZURE_TENANT_ID", "c54cdd2c-6e38-4c7c-8a3a-701741c360a9")

SPEECH_KEY: str = os.getenv("AZURE_SPEECH_KEY", "")
SPEECH_REGION: str = os.getenv("AZURE_SPEECH_REGION", "")
