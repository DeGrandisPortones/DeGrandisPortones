
from odoo import models, fields

class EmployeeLedgerStatementWizard(models.TransientModel):
    _name = "employee.ledger.statement.wizard"
    _description = "Employee Ledger Statement Wizard"

    employee_id = fields.Many2one("hr.employee", string="Empleado", required=True)
    date_from = fields.Date(string="Desde")
    date_to = fields.Date(string="Hasta")

    def action_open(self):
        self.ensure_one()
        domain = [("employee_id", "=", self.employee_id.id)]
        if self.date_from:
            domain.append(("date", ">=", self.date_from))
        if self.date_to:
            domain.append(("date", "<=", self.date_to))

        action = self.env.ref("hr_employee_ledger_statement18.action_employee_ledger_moves_statement").read()[0]
        # Apply filters
        action["domain"] = domain
        # Set defaults for new items and keep employee pinned in search
        ctx = dict(self.env.context or {})
        ctx.update({
            "default_employee_id": self.employee_id.id,
            "search_default_employee_id": self.employee_id.id,
        })
        action["context"] = ctx
        return action
