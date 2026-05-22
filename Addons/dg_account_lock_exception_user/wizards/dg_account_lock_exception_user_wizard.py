# -*- coding: utf-8 -*-
from datetime import timedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class DgAccountLockExceptionUserWizard(models.TransientModel):
    _name = "dg.account.lock.exception.user.wizard"
    _description = "Create an accounting lock exception for one user"

    company_id = fields.Many2one(
        "res.company",
        string="Compañía",
        required=True,
        default=lambda self: self.env.company,
    )
    user_id = fields.Many2one(
        "res.users",
        string="Usuario a desbloquear",
        required=True,
        domain="[('share', '=', False), ('active', '=', True)]",
        help="La excepción se creará únicamente para este usuario.",
    )
    lock_date_field = fields.Selection(
        selection=[
            ("fiscalyear_lock_date", "Bloquear todo"),
            ("tax_lock_date", "Bloquear declaración fiscal"),
            ("sale_lock_date", "Bloquear ventas"),
            ("purchase_lock_date", "Bloquear compras"),
        ],
        string="Bloqueo a flexibilizar",
        required=True,
        default="fiscalyear_lock_date",
    )
    company_lock_date = fields.Date(
        string="Fecha de bloqueo actual",
        compute="_compute_company_lock_date",
    )
    lock_date = fields.Date(
        string="Nueva fecha de bloqueo para ese usuario",
        required=True,
        help=(
            "Para permitir operar dentro del período bloqueado, esta fecha debe ser "
            "anterior a la fecha de bloqueo actual de la compañía."
        ),
    )
    end_datetime = fields.Datetime(
        string="Vigente hasta",
        help="Dejar vacío para que la excepción quede vigente hasta revocarla manualmente.",
    )
    reason = fields.Char(
        string="Motivo",
        default=lambda self: _("Desbloqueo contable por usuario"),
    )

    @api.depends("company_id", "lock_date_field")
    def _compute_company_lock_date(self):
        for wizard in self:
            wizard.company_lock_date = wizard.company_id[wizard.lock_date_field] if wizard.company_id and wizard.lock_date_field else False

    @api.onchange("company_id", "lock_date_field")
    def _onchange_lock_date_defaults(self):
        for wizard in self:
            company_lock_date = wizard.company_id[wizard.lock_date_field] if wizard.company_id and wizard.lock_date_field else False
            if company_lock_date:
                wizard.lock_date = company_lock_date - timedelta(days=1)
            else:
                wizard.lock_date = False

    @api.constrains("lock_date", "company_id", "lock_date_field", "end_datetime")
    def _check_dates(self):
        for wizard in self:
            if wizard.end_datetime and wizard.end_datetime <= fields.Datetime.now():
                raise ValidationError(_("La vigencia de la excepción debe ser futura."))
            if not wizard.company_id or not wizard.lock_date_field or not wizard.lock_date:
                continue
            company_lock_date = wizard.company_id[wizard.lock_date_field]
            if not company_lock_date:
                raise ValidationError(_("La compañía no tiene fecha de bloqueo definida para el bloqueo seleccionado."))
            if wizard.lock_date >= company_lock_date:
                raise ValidationError(_("La nueva fecha de bloqueo debe ser anterior a la fecha de bloqueo actual."))

    def action_create_exception(self):
        self.ensure_one()
        if not self.env.user.has_group("account.group_account_manager"):
            raise UserError(_("Solo un Administrador de Contabilidad puede crear excepciones de bloqueo."))

        self._check_dates()

        vals = {
            "company_id": self.company_id.id,
            "user_id": self.user_id.id,
            "reason": self.reason or _("Desbloqueo contable por usuario"),
            "end_datetime": self.end_datetime,
            self.lock_date_field: self.lock_date,
        }
        self.env["account.lock_exception"].create(vals)

        action = self.env["ir.actions.actions"]._for_xml_id(
            "dg_account_lock_exception_user.action_dg_account_lock_exception_history"
        )
        action["target"] = "current"
        return action
