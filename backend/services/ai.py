def get_ollama_client():
    try:
        from ollama import Client
        return Client()
    except Exception:
        return None
