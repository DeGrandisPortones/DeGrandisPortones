# Dflex Presupuestador SPA (Odoo 18 + React Vite)

Este bundle trae:
- `odoo_addons/dflex_presupuestador_spa`: addon Odoo 18 (models + API JSON + página /presupuestador)
- `frontend_vite`: React + Vite (TS) configurado para build dentro del addon

## 1) Instalación Odoo
1. Copiar `odoo_addons/dflex_presupuestador_spa` a tu addons_path.
2. Actualizar Apps list e instalar el módulo.
3. Crear rubros en: Presupuestador SPA > Rubros.

## 2) Desarrollo Frontend (modo dev)
Requisitos: Node 18+.
1. Entrar a `frontend_vite`
2. `npm install`
3. Levantar Odoo en `http://localhost:8069` (con portal habilitado y un usuario portal creado)
4. `npm run dev`
5. Abrir `http://localhost:5173`
   - Vite proxy manda `/api` y `/web` a Odoo.
   - El fetch usa `credentials: "include"` para la cookie de sesión.

## 3) Build para producción (servido por Odoo)
1. En `frontend_vite`: `npm run build`
2. Eso genera assets en:
   `odoo_addons/dflex_presupuestador_spa/static/app`
   y un `static/app/.vite/manifest.json`
3. En Odoo, abrir:
   `https://<tu-odoo>/presupuestador`
   (requiere login; portal o interno)

## Notas
- Los distribuidores deben ser usuarios **Portal** (sin licencia interna).
- La pricelist usada para precio base es la del Website (`website.pricelist_id`), idealmente "Predeterminado".
