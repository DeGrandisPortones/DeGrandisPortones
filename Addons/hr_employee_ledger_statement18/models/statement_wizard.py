
from odoo import models, fields, api, _

class HrEmployeeLedgerStatementWizard(models.TransientModel):
    _name = "hr.employee.ledger.statement.wizard"
    _description = "Estado de Cuenta de Empleado"

    employee_id = fields.Many2one("hr.employee", string="Empleado", required=True)
    date_from = fields.Date(string="Desde")
    date_to = fields.Date(string="Hasta")

    def action_open_statement(self):
        self.ensure_one()
        domain = [
            ("employee_id", "=", self.employee_id.id),
        ]
        if self.date_from:
            domain.append(("date", ">=", self.date_from))
        if self.date_to:
            domain.append(("date", "<=", self.date_to))
        # context for running balance
        ctx = {
            "search_default_employee_id": self.employee_id.id,
            "default_employee_id": self.employee_id.id,
            "statement_employee_id": self.employee_id.id,
        }
        if self.date_from:
            ctx["statement_date_from"] = self.date_from
        return {
            "type": "ir.actions.act_window",
            "name": _("Cuenta Corriente - %s") % (self.employee_id.name,),
            "res_model": "hr.employee.ledger.move",
            "view_mode": "list,form",
            "views": [
                (self.env.ref("hr_employee_ledger_statement18.view_employee_ledger_move_tree_statement").id, "list"),
                (self.env.ref("hr_employee_ledger_statement18.view_employee_ledger_move_form_statement").id, "form"),
            ],
            "domain": domain,
            "context": ctx,
            "target": "current",
        }
