# -*- coding: utf-8 -*-
from odoo import models, fields, api

class GateSpec(models.Model):
    _name = "x.gate.spec"
    _description = "Ficha de Portón"
    _order = "id desc"

    name = fields.Char("Nombre", required=True, index=True)
    import_batch_id = fields.Many2one("x.gate.import.batch", string="Lote de importación")
    data_json = fields.Json("Datos (JSON)")
    preview_html = fields.Html("Datos (tabla)", compute="_compute_preview_html", sanitize=False)
    company_id = fields.Many2one('res.company', string="Compañía", default=lambda self: self.env.company, readonly=False)

    @api.depends("data_json")
    def _compute_preview_html(self):
        for rec in self:
            d = rec.data_json or {}
            if not d:
                rec.preview_html = False
                continue
            items = sorted(d.items(), key=lambda x: x[0] or '')
            rows = "\n".join(
                f"<tr><th style='white-space:nowrap;padding:4px 8px'>{(k or '')}</th>"
                f"<td style='padding:4px 8px'>{(v or '')}</td></tr>"
                for k, v in items
            )
            rec.preview_html = f"""
                <div class="o_form_sheet">
                  <table class="table table-sm o_table" style="width:100%; table-layout:auto;">
                    <tbody>{rows}</tbody>
                  </table>
                </div>
            """
