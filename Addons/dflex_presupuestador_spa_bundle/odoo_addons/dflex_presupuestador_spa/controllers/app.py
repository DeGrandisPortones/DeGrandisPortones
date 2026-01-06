# -*- coding: utf-8 -*-
import json
import os
from odoo import http
from odoo.http import request


class PresupuestadorAppController(http.Controller):

    def _get_manifest(self):
        # Vite build creates: static/app/.vite/manifest.json
        module_path = os.path.dirname(os.path.dirname(__file__))  # controllers/..
        manifest_path = os.path.join(module_path, "static", "app", ".vite", "manifest.json")
        if not os.path.exists(manifest_path):
            return {}
        with open(manifest_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _get_vite_assets(self):
        manifest = self._get_manifest()
        # Default Vite entry: src/main.tsx
        entry = manifest.get("src/main.tsx") or manifest.get("src/main.jsx") or {}
        js = entry.get("file")
        css = entry.get("css", [])
        imports = entry.get("imports", [])

        # Collect imported CSS/JS if needed (kept simple)
        return {
            "entry_js": js,
            "entry_css": css,
            "imports": imports,
        }

    @http.route(["/presupuestador", "/presupuestador/<path:any_path>"], type="http", auth="user", website=True)
    def presupuestador_app(self, any_path=None, **kw):
        assets = self._get_vite_assets()
        return request.render("dflex_presupuestador_spa.presupuestador_spa_index", {
            "assets": assets,
        })
