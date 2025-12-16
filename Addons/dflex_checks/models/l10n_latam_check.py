from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class L10nLatamCheck(models.Model):
    _inherit = "l10n_latam.check"

    dflex_check_id = fields.Many2one(
        "dflex.check",
        string="Cheque",
        help="Cheque propio en cartera (DFlex) vinculado a este detalle.",
    )
    dflex_check_state = fields.Selection(related="dflex_check_id.state", string="Estado", store=True, readonly=True)
    dflex_check_bank_id = fields.Many2one(related="dflex_check_id.bank_id", string="Banco", store=True, readonly=True)
    dflex_check_type = fields.Selection(related="dflex_check_id.type", string="Tipo", store=True, readonly=True)
    dflex_check_issue_date = fields.Date(related="dflex_check_id.issue_date", string="Fecha emisión", store=True, readonly=True)
    dflex_check_amount = fields.Float(related="dflex_check_id.amount", string="Importe", store=True, readonly=True)
    dflex_check_partner_id = fields.Many2one(related="dflex_check_id.partner_id", string="Proveedor", store=True, readonly=True)

    @api.onchange("name", "payment_id", "original_journal_id")
    def _onchange_name_autolink_dflex(self):
        """Si el usuario tipea el número (name) en la grilla estándar de cheques,
        intentamos vincular automáticamente el cheque DFlex por número."""
        for rec in self:
            if rec.dflex_check_id or not rec.name:
                continue

            # Extrae un número del string (permite ceros a la izquierda)
            digits = "".join(ch for ch in rec.name if ch.isdigit())
            if not digits:
                continue
            try:
                num = int(digits)
            except Exception:
                continue

            company = rec.payment_id.company_id if rec.payment_id else rec.env.company

            # Intenta inferir banco desde el diario del pago (si existe)
            bank_id = False
            journal = getattr(rec.payment_id, "journal_id", False) if rec.payment_id else False
            if journal and getattr(journal, "bank_account_id", False) and journal.bank_account_id.bank_id:
                bank_id = journal.bank_account_id.bank_id.id

            domain = [
                ("state", "=", "available"),
                ("company_id", "=", company.id),
                ("payment_id", "=", False),
                ("number", "=", num),
            ]
            if bank_id:
                domain.append(("bank_id", "=", bank_id))

            check = rec.env["dflex.check"].search(domain, limit=1)
            if check:
                rec.dflex_check_id = check

    @api.onchange("dflex_check_id")
    def _onchange_dflex_check_id_sync_name(self):
        """Si el usuario elige el cheque por Many2one (si lo agrega por Studio),
        sincronizamos el 'Número' estándar para mantener compatibilidad."""
        for rec in self:
            if rec.dflex_check_id and (not rec.name or rec.name.isdigit()):
                # respeta ceros a la izquierda si el usuario los usa en su operación
                rec.name = str(rec.dflex_check_id.number).zfill(8)

    @api.constrains("dflex_check_id", "payment_id")
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
