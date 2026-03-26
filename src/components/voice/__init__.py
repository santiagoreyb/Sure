import os
import streamlit.components.v1 as components

# Create a _RELEASE constant. We'll set this to False while we're developing
# the component, and True when we're ready to package and distribute it.
_RELEASE = False

if not _RELEASE:
    # Use the local index.html directly
    parent_dir = os.path.dirname(os.path.abspath(__file__))
    build_dir = os.path.join(parent_dir, "frontend")
    _component_func = components.declare_component("realtime_voice", path=build_dir)
else:
    # In a full release you'd use a bundled path or an energetic server
    pass

def realtime_voice(speech_key: str, speech_region: str, text_to_speak: str = None, is_active: bool = False, key=None):
    """
    Shows a 'Live Voice' button that captures audio via mic, streams to Azure, and returns transcribed text.
    Also plays back audio via TTS if `text_to_speak` is provided and hasn't been spoken yet.
    """
    # Call through to our HTML/JS component.
    component_value = _component_func(
        speech_key=speech_key,
        speech_region=speech_region,
        text_to_speak=text_to_speak,
        is_active=is_active,
        key=key,
        default={}
    )
    
    return component_value
