from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class AccountPayment(models.Model):
    _inherit = "account.payment"

    dflex_check_line_ids = fields.One2many(
        "account.payment.dflex.check.line",
        "payment_id",
        string="Cheques (DFlex)",
        copy=False,
    )

    # Compatibilidad: mantener un único cheque en encabezado (solo si hay 1 en el detalle)
    dflex_check_id = fields.Many2one(
        "dflex.check",
        string="Cheque",
        compute="_compute_dflex_check_id",
        inverse="_inverse_dflex_check_id",
        store=True,
        readonly=False,
        tracking=True,
        help="(Compatibilidad) Se completa automáticamente cuando el pago tiene exactamente 1 cheque en el detalle.",
    )
    dflex_check_state = fields.Selection(
        related="dflex_check_id.state",
        string="Estado de emisión",
        store=True,
        readonly=True,
        tracking=True,
    )

    dflex_has_delivered_checks = fields.Boolean(
        string="Tiene cheques entregados",
        compute="_compute_dflex_has_delivered_checks",
    )

    @api.depends("dflex_check_line_ids.check_id")
    def _compute_dflex_check_id(self):
        for payment in self:
            checks = payment.dflex_check_line_ids.mapped("check_id")
            payment.dflex_check_id = checks[0].id if len(checks) == 1 else False

    def _inverse_dflex_check_id(self):
        for payment in self:
            if payment.dflex_check_id:
                # Reemplazar el detalle por una única línea con ese cheque
                payment.dflex_check_line_ids = [
                    (5, 0, 0),
                    (0, 0, {"check_id": payment.dflex_check_id.id}),
                ]
            else:
                # Si se limpia el cheque, limpiar también el detalle
                payment.dflex_check_line_ids = [(5, 0, 0)]

    @api.depends("dflex_check_line_ids.check_state", "state")
    def _compute_dflex_has_delivered_checks(self):
        for payment in self:
            payment.dflex_has_delivered_checks = any(
                line.check_state == "delivered" for line in payment.dflex_check_line_ids
            )

    def _dflex_get_checks(self):
        """Devolver cheques asociados al pago, soportando compatibilidad con encabezado."""
        self.ensure_one()
        checks = self.dflex_check_line_ids.mapped("check_id")
        # Compatibilidad: si no hay líneas pero hay cheque en encabezado, crear la línea
        if not checks and self.dflex_check_id:
            self.dflex_check_line_ids = [(0, 0, {"check_id": self.dflex_check_id.id})]
            checks = self.dflex_check_line_ids.mapped("check_id")
        return checks

    def action_post(self):
        res = super().action_post()
        for payment in self:
            checks = payment._dflex_get_checks()
            for check in checks:
                if check.company_id != payment.company_id:
                    raise ValidationError(
                        _("El cheque %s pertenece a otra compañía.") % check.display_name
                    )
                if check.payment_id and check.payment_id != payment:
                    raise ValidationError(
                        _("El cheque %s está vinculado a otro pago (%s).")
                        % (check.display_name, check.payment_id.display_name)
                    )
                if check.state != "available":
                    selection = dict(check._fields["state"].selection)
                    raise ValidationError(
                        _("Solo se pueden entregar cheques en estado Disponible. Estado actual: %s")
                        % selection.get(check.state, check.state)
                    )
                check.write({"state": "delivered", "payment_id": payment.id})
        return res

    def action_cancel(self):
        res = super().action_cancel()
        for payment in self:
            checks = payment._dflex_get_checks()
            for check in checks:
                # Solo revertir si este pago fue quien lo entregó
                if check.payment_id == payment and check.state == "delivered":
                    check.write({"state": "available", "payment_id": False})
        return res

    def action_dflex_mark_check_returned(self):
        for payment in self:
            checks = payment._dflex_get_checks()
            if not checks:
                raise ValidationError(_("No hay cheques asociados a este pago."))
            for check in checks:
                if check.payment_id and check.payment_id != payment:
                    raise ValidationError(
                        _("El cheque %s está vinculado a otro pago (%s).")
                        % (check.display_name, check.payment_id.display_name)
                    )
                if check.state != "delivered":
                    selection = dict(check._fields["state"].selection)
                    raise ValidationError(
                        _("Solo se puede marcar como Devuelto un cheque en estado Entregado. Estado actual: %s")
                        % selection.get(check.state, check.state)
                    )
                check.write({"state": "returned", "payment_id": payment.id})
        return True
