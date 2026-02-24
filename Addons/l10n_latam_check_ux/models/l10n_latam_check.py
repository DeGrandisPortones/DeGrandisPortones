from odoo import _, api, fields, models
from odoo.exceptions import UserError


class l10nLatamAccountPaymentCheck(models.Model):
    _inherit = "l10n_latam.check"

    check_add_debit_button = fields.Boolean(
        related="original_journal_id.check_add_debit_button", readonly=True
    )

    first_operation = fields.Many2one(
        "account.payment",
        compute="_compute_first_operation",
        store=True,
        readonly=True,
    )
    # Origen (de dónde vino el cheque)
    date = fields.Date(related="first_operation.date")
    memo = fields.Char(related="payment_id.memo")
    origin_move_id = fields.Many2one(
        comodel_name="account.move",
        related="payment_id.move_id",
        string="Asiento Origen",
        readonly=True,
    )

    # Destino (última operación del cheque: depósito, pago a proveedor, transferencia, etc.)
    last_operation_id = fields.Many2one(
        comodel_name="account.payment",
        string="Operación Destino",
        compute="_compute_last_operation_id",
        store=True,
        readonly=True,
    )
    last_operation_move_id = fields.Many2one(
        comodel_name="account.move",
        related="last_operation_id.move_id",
        string="Asiento Destino",
        readonly=True,
    )

    company_id = fields.Many2one(
        compute="_compute_company_id", store=True, compute_sudo=True, comodel_name="res.company"
    )
    operation_ids = fields.Many2many(check_company=False)
    payment_state = fields.Selection(
        related="payment_id.state",
        readonly=True,
    )

    @api.depends(
        "operation_ids.state",
        "operation_ids.l10n_latam_move_check_ids_operation_date",
        "payment_id.state",
        "payment_id.l10n_latam_move_check_ids_operation_date",
    )
    def _compute_last_operation_id(self):
        for rec in self:
            last_op = rec._get_last_operation()
            # _get_last_operation devuelve recordset (0 o 1). Si no hay, usamos payment_id como fallback.
            rec.last_operation_id = (last_op and last_op.id) or rec.payment_id.id or False

    @api.depends("operation_ids.state", "payment_id.state")
    def _compute_company_id(self):
        for rec in self:
            last_operation = rec._get_last_operation() or rec.payment_id
            rec.company_id = last_operation.company_id

    @api.depends("operation_ids.state", "payment_id.state")
    def _compute_first_operation(self):
        for rec in self:
            all_operations = rec.payment_id + rec.operation_ids
            valid_ops = all_operations.filtered(lambda x: x.state in ["in_process", "paid"])
            sorted_ops = valid_ops.sorted(key=lambda payment: (payment.date, payment._origin.id))
            rec.first_operation = sorted_ops[:1].id or False

    def button_open_check_operations(self):
        action = super(l10nLatamAccountPaymentCheck, self.sudo()).button_open_check_operations()
        self.ensure_one()
        operations = self.operation_ids.sorted(lambda r: r.l10n_latam_move_check_ids_operation_date, reverse=True)
        operations = (operations + self.payment_id).filtered(
            lambda x: x.state not in ["draft", "canceled"] and x.company_id == self.company_id
        )
        action = {
            "name": _("Check Operations"),
            "type": "ir.actions.act_window",
            "res_model": "account.payment",
            "views": [
                (self.env.ref("l10n_latam_check.view_account_third_party_check_operations_tree").id, "list"),
                (False, "form"),
            ],
            "context": {"create": False},
            "domain": [("id", "in", operations.ids)],
        }
        return action

    def _get_last_operation(self):
        super()._get_last_operation()
        self.ensure_one()
        return (
            (self.payment_id + self.operation_ids)
            .filtered(lambda x: x.state not in ["draft", "canceled"] and x.l10n_latam_move_check_ids_operation_date)
            .sorted(key=lambda payment: (payment.l10n_latam_move_check_ids_operation_date))[-1:]
        )

    # ---------- Acciones para botones de grilla ----------
    def action_open_origin_payment(self):
        self.ensure_one()
        if not self.payment_id:
            raise UserError(_("No hay recibo/origen para este cheque."))
        return {
            "type": "ir.actions.act_window",
            "res_model": "account.payment",
            "view_mode": "form",
            "res_id": self.payment_id.id,
            "target": "current",
        }

    def action_open_origin_move(self):
        self.ensure_one()
        if not self.origin_move_id:
            raise UserError(_("El recibo/origen no tiene asiento contable."))
        return {
            "type": "ir.actions.act_window",
            "res_model": "account.move",
            "view_mode": "form",
            "res_id": self.origin_move_id.id,
            "target": "current",
        }

    def action_open_dest_payment(self):
        self.ensure_one()
        if not self.last_operation_id:
            raise UserError(_("No se encontró una operación destino para este cheque."))
        return {
            "type": "ir.actions.act_window",
            "res_model": "account.payment",
            "view_mode": "form",
            "res_id": self.last_operation_id.id,
            "target": "current",
        }

    def action_open_dest_move(self):
        self.ensure_one()
        if not self.last_operation_move_id:
            raise UserError(_("La operación destino no tiene asiento contable."))
        return {
            "type": "ir.actions.act_window",
            "res_model": "account.move",
            "view_mode": "form",
            "res_id": self.last_operation_move_id.id,
            "target": "current",
        }
