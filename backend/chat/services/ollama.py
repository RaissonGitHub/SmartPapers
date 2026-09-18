import os

import ollama

cliente_ollama = ollama.Client(host=os.getenv("OLLAMA_HOST", "http://localhost:11434"))


def chamaarOllama(modelo, msg):
    result = cliente_ollama.generate(model=modelo, prompt=msg)
    return result["response"]
