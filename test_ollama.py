import requests

try:
    res = requests.post("http://localhost:11434/api/chat", json={
        "model": "llama3",
        "messages": [
            {"role": "user", "content": "Hola, ¿estás disponible?"}
        ],
        "stream": False
    }, timeout=10)
    print("Ollama status:", res.status_code)
    print("Response:", res.json()["message"]["content"])
except Exception as e:
    print("Ollama Error:", e)
