import base64

def convert_audio_to_base64(binary_audio_data: bytes):
    """Convert audio object data to base64."""
    # binary_audio_data = audio_obj.data
    return base64.b64encode(binary_audio_data).decode("utf-8")
