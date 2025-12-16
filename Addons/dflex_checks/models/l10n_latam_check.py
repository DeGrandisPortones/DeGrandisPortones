from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class L10nLatamCheck(models.Model):
    _inherit = "l10n_latam.check"

    dflex_check_id = fields.Many2one(
        "dflex.check",
        string="Cheque",
        help="Cheque propio en cartera (DFlex) vinculado a este detalle.",
    )

    # Relateds para mostrar columnas en la grilla estándar de cheques del pago
    dflex_check_state = fields.Selection(related="dflex_check_id.state", string="Estado", store=True, readonly=True)
    dflex_check_bank_id = fields.Many2one(related="dflex_check_id.bank_id", string="Banco", store=True, readonly=True)
    dflex_check_type = fields.Selection(related="dflex_check_id.type", string="Tipo", store=True, readonly=True)
    dflex_check_issue_date = fields.Date(related="dflex_check_id.issue_date", string="Fecha emisión", store=True, readonly=True)

    dflex_check_currency_id = fields.Many2one(
        related="dflex_check_id.currency_id",
        string="Moneda",
        store=True,
        readonly=True,
    )
    dflex_check_amount = fields.Monetary(
        related="dflex_check_id.amount",
        currency_field="dflex_check_currency_id",
        string="Importe",
        store=True,
        readonly=True,
    )

    dflex_check_partner_id = fields.Many2one(
        related="dflex_check_id.partner_id",
        string="Proveedor",
        store=True,
        readonly=True,
    )

    def _dflex_find_candidate_domain(self):
        """Dominio para buscar un cheque DFlex a partir del número tipeado.
        Se filtra por compañía y por estado disponible. Si podemos inferir banco por el diario del pago,
        también lo filtramos por banco."""
        self.ensure_one()
        domain = [
            ("state", "=", "available"),
            ("company_id", "=", self.company_id.id or self.env.company.id),
            ("payment_id", "=", False),
        ]

        # Inferir banco desde el diario del pago si existe
        bank_id = False
        journal = self.original_journal_id
        if journal and getattr(journal, "bank_account_id", False) and journal.bank_account_id.bank_id:
            bank_id = journal.bank_account_id.bank_id.id
        if bank_id:
            domain.append(("bank_id", "=", bank_id))
        return domain

    @api.onchange("dflex_check_id")
    def _onchange_dflex_check_id_set_number(self):
        for rec in self:
            if rec.dflex_check_id and rec.dflex_check_id.number:
                # mantiene ceros a la izquierda según práctica local
                rec.name = str(rec.dflex_check_id.number).zfill(8)

    @api.onchange("name", "payment_id", "original_journal_id")
    def _onchange_name_autolink_dflex(self):
        """Si el usuario tipea el número (name) en la grilla estándar,
        intentamos vincular automáticamente el cheque DFlex por número."""
        for rec in self:
            if rec.dflex_check_id or not rec.name:
                continue

            digits = "".join(ch for ch in rec.name if ch.isdigit())
            if not digits:
                continue

            number = int(digits)
            domain = rec._dflex_find_candidate_domain() + [("number", "=", number)]
            candidate = self.env["dflex.check"].search(domain, limit=1)
            if candidate:
                rec.dflex_check_id = candidate
                # Mejor UX: si este detalle pertenece a un pago existente,
                # reflejamos el cheque también en el encabezado.
                if rec.payment_id:
                    rec.payment_id.dflex_check_id = candidate
    @api.constrains("dflex_check_id")
    def _constrains_dflex_check_available(self):
        for rec in self:
            if not rec.dflex_check_id:
                continue
            if rec.dflex_check_id.state != "available":
                selection = dict(rec.dflex_check_id._fields["state"].selection)
                raise ValidationError(
                    _("El cheque %s no está disponible (estado actual: %s).")
                    % (rec.dflex_check_id.display_name, selection.get(rec.dflex_check_id.state, rec.dflex_check_id.state))
                )

    # -------------------------------------------------------------------------
    # Sincronización con el encabezado del pago
    # -------------------------------------------------------------------------
    def _dflex_sync_payment_header(self, payments=None):
        """Asegura que el campo account.payment.dflex_check_id refleje el cheque
        elegido en el detalle.

        - Si hay exactamente 1 cheque distinto en los detalles, lo setea en el pago.
        - Si hay 0 o más de 1, limpia el encabezado (evita ambigüedad).
        """
        payments = payments or self.mapped("payment_id")
        payments = payments.filtered(lambda p: p)
        if not payments:
            return

        for payment in payments:
            details = self.search([("payment_id", "=", payment.id), ("dflex_check_id", "!=", False)])
            dflex_checks = details.mapped("dflex_check_id")
            payment.dflex_check_id = dflex_checks[0] if len(dflex_checks) == 1 else False

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records._dflex_sync_payment_header()
        return records

    def write(self, vals):
        payments = self.mapped("payment_id")
        res = super().write(vals)
        # Si se modificó el vínculo o el pago asociado, re-sincronizamos
        if any(k in vals for k in ("dflex_check_id", "payment_id")):
            self._dflex_sync_payment_header(payments=(self.mapped("payment_id") | payments))
        return res

    def unlink(self):
        payments = self.mapped("payment_id")
        res = super().unlink()
        self._dflex_sync_payment_header(payments=payments)
        return res
