# -*- coding: utf-8 -*-
from odoo import models, _


class PortonLauncher(models.TransientModel):
    _name = "x_dflex.porton.launcher"
    _description = "Lanzador de Portones"

    def action_open_list(self):
        action = self.env.ref('dflex_portones_ui.action_x_dflex_porton_ui', raise_if_not_found=False)
        if action:
            return action.read()[0]
        return {
            "type": "ir.actions.act_window",
            "name": _("Portones"),
            "res_model": "x_dflex.porton",
            "view_mode": "list,form",
        }

    def action_open_import(self):
        action = self.env.ref('dflex_portones_import.action_porton_import_wizard', raise_if_not_found=False)
        if action:
            # abrir como modal
            res = action.read()[0]
            res["target"] = "new"
            return res
        return {"type": "ir.actions.client", "tag": "display_notification",
                "params": {"title": _("Importación"), "message": _("No encontré el wizard de importación."), "sticky": False}}
