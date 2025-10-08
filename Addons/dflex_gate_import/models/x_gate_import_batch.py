# -*- coding: utf-8 -*-
from odoo import models, fields

class GateImportBatch(models.Model):
    _name = "x.gate.import.batch"
    _check_company_auto = True
    _description = "Lote de importación de portones (Excel)"
    _order = "id desc"

    name = fields.Char(default="Importación", required=True)
    file_data = fields.Binary("Archivo Excel", attachment=True)
    file_name = fields.Char("Nombre de archivo")
    sheet_name = fields.Char("Hoja importada")
    row_count = fields.Integer("Filas importadas")
    note = fields.Text("Notas")
    gate_spec_ids = fields.One2many("x.gate.spec", "import_batch_id", string="Fichas creadas")
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company, string="Compañía",  readonly=False)
