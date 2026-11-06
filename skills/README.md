# skills/

Carpeta reservada para comandos "enchufables".

Mientras tanto, para añadir un comando nuevo solo necesitas 3 pasos
(está todo detallado en el README, sección *"Cómo añadir tus propios comandos"*):

1. Función en `actions/` → recibe `slots` y devuelve un `str`.
2. Registrar en `HANDLERS` de `actions/__init__.py`.
3. Regla regex en `_RULES` de `brain/local_intent.py`.

Cuando tengas varios, podemos moverlos aquí como módulos independientes
con un registro automático (decorador `@skill`).
