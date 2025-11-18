from odoo import models, fields, api, _

class HrEmployeeLedgerStatementWizard(models.TransientModel):
    _name = "hr.employee.ledger.statement.wizard"
    _description = "Employee Ledger Statement Wizard"

    employee_id = fields.Many2one("hr.employee", string="Empleado", required=True)
    date_from = fields.Date(string="Desde")
    date_to = fields.Date(string="Hasta")

    def action_open_statement(self):
        self.ensure_one()
        domain = [('employee_id', '=', self.employee_id.id)]
        if self.date_from:
            domain.append(('date', '>=', self.date_from))
        if self.date_to:
            domain.append(('date', '<=', self.date_to))
        action = {
            'name': _('Cuenta Corriente'),
            'type': 'ir.actions.act_window',
            'res_model': 'hr.employee.ledger.move',
            'view_mode': 'list,form',
            'views': [(self.env.ref('hr_employee_ledger_statement18.view_employee_ledger_move_tree_statement').id, 'list'),
                      (False, 'form')],
            'domain': domain,
            'context': {
                'search_default_employee_id': self.employee_id.id,
                'default_employee_id': self.employee_id.id,
                'statement_date_from': self.date_from and fields.Date.to_string(self.date_from) or False,
            }
        }
        return action