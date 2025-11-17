
# -*- coding: utf-8 -*-
from collections import defaultdict
from datetime import date
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

class HrEmployeeLedgerBatchWizard(models.TransientModel):
    _name = "hr.employee.ledger.batch.wizard"
    _description = "Wizard de cierre mensual (A/B)"
    _check_company_auto = True

    company_id = fields.Many2one('res.company', default=lambda s: s.env.company, required=True)
    currency_id = fields.Many2one(related='company_id.currency_id', store=True, readonly=True)

    payment_type = fields.Selection([('a', 'Pago A (dinero)'), ('b', 'Pago B (alimentos)')], default='a', required=True, string='Tipo')
    date_from = fields.Date(string='Desde', default=lambda s: date.today().replace(day=1))
    date_to = fields.Date(string='Hasta', default=fields.Date.context_today)

    journal_id = fields.Many2one('account.journal', string='Diario', domain=[('type','in',('general','cash','bank'))])
    debit_account_id = fields.Many2one('account.account', string='Cuenta débito (Anticipos)', domain=[('deprecated','=',False)])

    include_drafts = fields.Boolean(string='Incluir borradores', default=False, help="Si se marca, también se incluyen movimientos en borrador.")
    confirm_drafts = fields.Boolean(string='Asentar borradores', default=True, help="Si se incluye borrador, los asienta automáticamente.")
    memo = fields.Char(string='Referencia', default='Cierre anticipos RRHH')

    total_moves = fields.Integer(string='Cantidad de movimientos', compute='_compute_totals', store=False)
    total_amount = fields.Monetary(string='Total a cerrar', currency_field='currency_id', compute='_compute_totals', store=False)

    line_ids = fields.One2many('hr.employee.ledger.batch.wizard.line', 'wizard_id', string='Resumen por cuenta')
    employee_line_ids = fields.One2many('hr.employee.ledger.batch.wizard.employee.line', 'wizard_id', string='Detalle por empleado')

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        company = self.env.company
        if not res.get('journal_id') and company.employee_batch_journal_id:
            res['journal_id'] = company.employee_batch_journal_id.id
        # default debit account from company according to type A
        if not res.get('debit_account_id') and company.employee_advance_account_a_id:
            res['debit_account_id'] = company.employee_advance_account_a_id.id
        return res

    def _domain_moves(self):
        dom = [('company_id','=', self.company_id.id),
               ('payment_type','=', self.payment_type),
               ('batch_id','=', False)]
        if self.include_drafts:
            dom.append(('state','in',('draft','posted')))
        else:
            dom.append(('state','=','posted'))
        if self.date_from:
            dom.append(('date','>=', self.date_from))
        if self.date_to:
            dom.append(('date','<=', self.date_to))
        return dom

    @api.onchange('payment_type','date_from','date_to','include_drafts')
    def _onchange_refresh_preview(self):
        self._load_preview()

    def _load_preview(self):
        Move = self.env['hr.employee.ledger.move']
        moves = Move.search(self._domain_moves())
        # group by account for credits
        acc_map = defaultdict(lambda: {'amount':0.0, 'count':0})
        emp_map = defaultdict(lambda: {'amount':0.0, 'count':0})
        for m in moves:
            if m.account_src_id:
                acc_map[m.account_src_id.id]['amount'] += (m.amount or 0.0)
                acc_map[m.account_src_id.id]['count'] += 1
            emp_map[m.employee_id.id]['amount'] += (m.amount or 0.0)
            emp_map[m.employee_id.id]['count'] += 1

        self.line_ids = [(5,0,0)] + [(0,0,{'account_id': acc, 'amount':vals['amount'], 'count_moves': vals['count']}) for acc, vals in acc_map.items()]
        self.employee_line_ids = [(5,0,0)] + [(0,0,{'employee_id': emp, 'amount':vals['amount'], 'count_moves': vals['count']}) for emp, vals in emp_map.items()]

    @api.depends('line_ids.amount','line_ids.count_moves')
    def _compute_totals(self):
        for w in self:
            w.total_amount = sum(l.amount for l in w.line_ids)
            w.total_moves = sum(l.count_moves for l in w.line_ids)

    def action_generate(self):
        self.ensure_one()
        Move = self.env['hr.employee.ledger.move']
        moves = Move.search(self._domain_moves())
        if not moves:
            raise UserError(_("No hay movimientos pendientes para generar el lote."))

        if self.include_drafts and self.confirm_drafts:
            for m in moves.filtered(lambda x: x.state == 'draft'):
                m.action_post()

        company = self.company_id
        # Use the wizard-provided journal/account, fallback to company config
        journal = self.journal_id or company.employee_batch_journal_id
        if not journal:
            raise UserError(_("Seleccione el Diario."))

        debit_account = self.debit_account_id
        if not debit_account:
            debit_account = company.employee_advance_account_a_id if self.payment_type == 'a' else company.employee_advance_account_b_id
        if not debit_account:
            raise UserError(_("Seleccione la Cuenta de anticipos para este tipo (%s).") % self.payment_type.upper())

        # determine period from available moves
        dates = [m.date for m in moves if m.date]
        dfrom = min(dates) if dates else fields.Date.context_today(self)
        dto = max(dates) if dates else fields.Date.context_today(self)

        # Build credit lines grouped by account
        acc_map = defaultdict(float)
        for m in moves:
            if m.account_src_id:
                acc_map[m.account_src_id.id] += (m.amount or 0.0)

        batch_vals = {
            'company_id': company.id,
            'payment_type': self.payment_type,
            'date_from': dfrom,
            'date_to': dto,
            'journal_id': journal.id,
            'debit_account_id': debit_account.id,
            'memo': self.memo or _('Cierre anticipos RRHH'),
        }

        batch = self.env['hr.employee.ledger.batch'].create(batch_vals)
        credit_lines = [(0,0,{'account_id': acc_id, 'amount': amt, 'name': _('Salida de %s') % self.env['account.account'].browse(acc_id).name}) for acc_id, amt in acc_map.items() if amt]
        if credit_lines:
            batch.write({'credit_line_ids': credit_lines})

        # Fill employee summary
        emp_map = defaultdict(lambda: {'amount':0.0, 'count':0})
        for m in moves:
            emp_map[m.employee_id.id]['amount'] += (m.amount or 0.0)
            emp_map[m.employee_id.id]['count'] += 1
        emp_lines = [(0,0,{'employee_id': eid, 'amount': d['amount'], 'count_moves': d['count']}) for eid, d in emp_map.items()]
        if emp_lines:
            batch.write({'employee_line_ids': emp_lines})

        # Link moves
        moves.write({'batch_id': batch.id})

        action = self.env.ref('hr_employee_ledger.action_hr_employee_ledger_batch').read()[0]
        action['res_id'] = batch.id
        action['view_mode'] = 'form'
        return action


class HrEmployeeLedgerBatchWizardLine(models.TransientModel):
    _name = 'hr.employee.ledger.batch.wizard.line'
    _description = 'Resumen por cuenta - Wizard cierre'
    wizard_id = fields.Many2one('hr.employee.ledger.batch.wizard', required=True, ondelete='cascade')
    account_id = fields.Many2one('account.account', string='Cuenta crédito', required=True)
    count_moves = fields.Integer(string='Movimientos')
    amount = fields.Monetary(string='Importe', currency_field='currency_id')
    currency_id = fields.Many2one(related='wizard_id.currency_id', store=True, readonly=True)

class HrEmployeeLedgerBatchWizardEmployeeLine(models.TransientModel):
    _name = 'hr.employee.ledger.batch.wizard.employee.line'
    _description = 'Detalle por empleado - Wizard cierre'
    wizard_id = fields.Many2one('hr.employee.ledger.batch.wizard', required=True, ondelete='cascade')
    employee_id = fields.Many2one('hr.employee', string='Empleado', required=True)
    count_moves = fields.Integer(string='Movimientos')
    amount = fields.Monetary(string='Importe', currency_field='currency_id')
    currency_id = fields.Many2one(related='wizard_id.currency_id', store=True, readonly=True)
