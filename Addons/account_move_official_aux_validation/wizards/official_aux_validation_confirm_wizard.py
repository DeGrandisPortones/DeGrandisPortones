from odoo import fields, models


class OfficialAuxValidationConfirmWizard(models.TransientModel):
    _name = "official.aux.validation.confirm.wizard"
    _description = "Confirmación de validación Oficial vs Auxiliar"

    move_ids = fields.Many2many("account.move", string="Movimientos", required=True)
    message = fields.Text(string="Mensaje", readonly=True)

    def action_continue(self):
        self.ensure_one()
        self.move_ids.with_context(official_aux_validation_confirmed=True).action_post()
        return {"type": "ir.actions.act_window_close"}
