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
