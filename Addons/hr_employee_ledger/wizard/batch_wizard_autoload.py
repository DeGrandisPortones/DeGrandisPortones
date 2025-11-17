# -*- coding: utf-8 -*-
from odoo import api, models

class HrEmployeeLedgerBatchWizardAutoload(models.TransientModel):
    _inherit = 'hr.employee.ledger.batch.wizard'

    @api.model
    def create(self, vals):
        rec = super().create(vals)
        # Si el método privado existe, lo llamamos para llenar el preview
        if hasattr(rec, '_load_preview'):
            try:
                rec._load_preview()
            except Exception:
                # Evitar que el wizard falle durante la creación si hay datos inconsistentes
                pass
        return rec

    @api.onchange('type', 'date_start', 'date_end')
    def _onchange_filters_autoload(self):
        if self and hasattr(self, '_load_preview'):
            try:
                self._load_preview()
            except Exception:
                pass

    def action_load_preview(self):
        self.ensure_one()
        if hasattr(self, '_load_preview'):
            self._load_preview()
        return False
