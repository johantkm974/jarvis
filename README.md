# Jarvis 🤖

Asistente personal para tu PC (Windows) hecho en Python: te escucha, abre
programas, levanta MySQL, revisa puertos, crea archivos y te ayuda a programar.

## Arquitectura (híbrido, RAM controlada)

```
jarvis/
├── jarvis.py              # punto de entrada (modos: texto, ptt, voz)
├── config.py              # ajustes (lee .env)
├── brain/
│   ├── router.py          # decide: ¿regla local o API?
│   ├── local_intent.py    # reglas: 0 RAM, 0 costo, instantáneo
│   └── api_client.py      # OpenAI/Groq/LM Studio: solo si hace falta
├── voice/                 # wake word + whisper + tts (carga bajo demanda)
├── actions/               # apps, XAMPP/MySQL, puertos, archivos
└── workspace/             # donde se crean tus archivos por defecto
```

**Por qué híbrido:** los comandos del día a día ("abre youtube", "levanta mysql")
se resuelven con reglas locales → sin costo y sin internet. Solo cuando la regla
no reconoce el texto se consulta la API. Nunca se cargan a la vez un modelo
local de voz y la API: el whisper solo se carga cuando hablas, y el cerebro
API nunca descarga modelos locales.

## Instalación

```powershell
cd C:\Users\Admin\jarvis
pip install -r requirements.txt          # núcleo (psutil + openai)
# opcional, voz:
pip install -r requirements-voz.txt
copy .env.example .env                   # y pon tu OPENAI_API_KEY
```

## Uso

```powershell
python jarvis.py                 # modo texto (funciona sin instalar la voz)
python jarvis.py --cmd "levanta mysql"
python jarvis.py --ptt           # pulsas Enter y hablas
python jarvis.py --voz           # dices "hey jarvis" y hablas
python jarvis.py --sin-tts       # sin respuesta hablada
```

## Comandos

| Dices / escribes | Acción |
|---|---|
| `abre youtube` / `abre chatgpt` / `abre github` | Navegador |
| `abre chrome`, `abre calculadora`, `abre vscode` | Programas instalados |
| `abre opencode` | OpenCode en una terminal nueva |
| `levanta mysql` / `para mysql` / `estado de mysql` | XAMPP (arranca/para/comprueba) |
| `que puertos` | Lista puertos en escucha + proceso dueño |
| `que proceso usa el puerto 3300` | Quién usa ese puerto |
| `que procesos` | Top 10 por memoria |
| `como estas` | CPU / RAM / disco |
| `crea carpeta proyectos` | Carpeta en `workspace/` |
| `crea archivo notas.txt` | Archivo vacío |
| `escribe Hola mundo en archivo notas.txt` | Añade texto |
| `escribe: mi dictado` | Añade a `workspace/dictado.txt` |
| `lee archivo notas.txt` · `lista archivos` · `que hay en descargas` | Leer/listar |
| `que hora` · `que dia` · `ayuda` · `salir` | Varios |

Cualquier cosa que no esté en la tabla va al **cerebro API** (si configuraste la
clave). Ejemplos: "explícame este error", "escríbeme una función que lea un CSV",
"hazme un plan para el proyecto".

## Cómo añadir tus propios comandos

1. Crea la función en `actions/` (o un archivo nuevo).
2. Regístrala en `HANDLERS` dentro de `actions/__init__.py`.
3. Añade la regla (regex) en `_RULES` de `brain/local_intent.py`.

Sin tocar nada más: `router.py` ya sabe enchufarla.

## Seguridad

- Los archivos se crean por defecto en `jarvis/workspace/` (rutas absolutas también valen).
- Jarvis **no** ejecuta acciones destructivas (borrar/mover) todavía: pídelo y se añade
  con confirmación obligatoria antes de ejecutar.
- La API solo recibe el texto que tú escribes; no se suben archivos.

## Requisitos de voz

- Micrófono funcionando en Windows (prueba con `soundrecorder`).
- `pyaudio` viene como wheel en pip (sin compilar).
- La wake word usa modelos **ONNX** (`hey_jarvis_v0.1.onnx`): en Windows no existe
  `tflite-runtime`, así que `voice/wake.py` fuerza el framework ONNX. Se descargan
  solos la primera vez (~5 MB).
- La primera vez que usas `--ptt`, `faster-whisper` descarga el modelo `base`
  (~150 MB, **ya pre-descargado en este equipo**) y ocupa ~150 MB de RAM
  **solo mientras escucha**. Libéralo con `voice.stt.unload()`.
- Si `--voz` no arranca, usa `--ptt` (Enter y hablas): es más fiable.
