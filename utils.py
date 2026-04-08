import os
from thefuzz import process

def load_user_list(filepath):
    if not os.path.exists(filepath):
        print(f"[*] Archivo {filepath} no encontrado. Creando vacio...")
        with open(filepath, 'w', encoding='utf-8') as f:
            pass
        return []
    with open(filepath, 'r', encoding='utf-8') as f:
        return [line.strip() for line in f if line.strip()]

def get_fuzzy_match(name, choices, threshold=70):
    if choices:
        best_match = process.extractOne(name, choices)
        if best_match and best_match[1] >= threshold:
            return best_match[0]
    return None
