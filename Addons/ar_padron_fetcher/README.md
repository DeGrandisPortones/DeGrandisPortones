# AR Padrón (AFIP/ARCA) – CUIT Autocomplete (Odoo 18)

Este módulo agrega un botón **"Actualizar desde Padrón (AFIP/ARCA)"** en Contactos (Argentina).
Funciona **de inmediato en modo mock**, y deja listo el hook para producción (AFIP/ARCA).

## Instalación (Odoo.sh)
1. Copiar esta carpeta dentro de tu repo (por ejemplo `custom/addons/ar_padron_fetcher/`).
2. Commit & push → esperar a que el build termine.
3. En la base: Activar *Modo Desarrollador* → **Apps → Actualizar lista** → Instalar *AR Padrón (AFIP/ARCA) – CUIT Autocomplete*.

> Sugerido: agregar `zeep` a `requirements.txt` del repo (Odoo.sh lo instalará).

## Configuración
Ajustes → **AFIP/ARCA – Padrón**: elegí el entorno y (para test/prod) cargá **certificado/clave**.
Mientras tanto, podés dejar **"Usar datos de ejemplo (mock)"** activo para probar el botón.

## Uso
En el contacto:
- País = Argentina
- CUIT en el campo **VAT** (11 dígitos)
- Click en **Actualizar desde Padrón (AFIP/ARCA)**

## Producción (AFIP/ARCA)
El archivo `models/afip_service.py` incluye:
- Validación de CUIT y lógica de mapeo
- Hook para implementar la llamada real al **Padrón A5** via WSAA + SOAP.
  Podés implementar `models/wsaa_zeep.py` con:
  - `get_token_sign(env, conf)` para WSAA (LoginCms)
  - `padron_a5_get_person(env, token, sign, cuit, environment)` para el A5
o integrar una librería (por ej. `pyafipws`) desde `external_dependencies`.