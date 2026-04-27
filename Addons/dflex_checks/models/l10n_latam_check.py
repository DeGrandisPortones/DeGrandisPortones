from odoo import api, fields, models


class L10nLatamCheck(models.Model):
    _inherit = "l10n_latam.check"

    dflex_check_id = fields.Many2one(
        "dflex.check",
        string="Cheque propio disponible",
        copy=False,
        index=True,
        domain="[('state', '=', 'available'), ('company_id', '=', company_id)]",
        help="Cheque propio generado desde una chequera DFlex. Usar este campo en pagos con método Cheques propios.",
    )
    dflex_check_journal_id = fields.Many2one(
        related="dflex_check_id.journal_id",
        string="Diario cheque propio",
        readonly=True,
    )
    dflex_check_type = fields.Selection(
        related="dflex_check_id.type",
        string="Tipo cheque propio",
        readonly=True,
    )
    dflex_check_state = fields.Selection(
        related="dflex_check_id.state",
        string="Estado cheque propio",
        readonly=True,
    )

    def _dflex_sync_from_selected_check(self):
        for rec in self.filtered("dflex_check_id"):
            check = rec.dflex_check_id

            vals = {}
            if "name" in rec._fields:
                vals["name"] = check.name
            if "number" in rec._fields:
                vals["number"] = check.number
            if "bank_id" in rec._fields and check.bank_id:
                vals["bank_id"] = check.bank_id.id
            if "payment_date" in rec._fields and check.payment_date and not rec.payment_date:
                vals["payment_date"] = check.payment_date
            if "amount" in rec._fields and check.amount and not rec.amount:
                vals["amount"] = check.amount

            company = rec.company_id or rec.payment_id.company_id or rec.env.company
            company_partner = company.partner_id
            company_vat = company_partner.vat or ""
            company_name = company_partner.commercial_company_name or company_partner.name or company.display_name

            # En cheques propios el emisor es la empresa que paga.
            for field_name in ("issuer_vat", "owner_vat"):
                if field_name in rec._fields:
                    vals[field_name] = company_vat
            for field_name in ("issuer_name", "owner_name", "x_studio_emisor_nombre"):
                if field_name in rec._fields:
                    vals[field_name] = company_name

            # El campo Studio Tipo puede ser obligatorio en algunas bases. Para cheques propios
            # lo cargamos automáticamente desde la chequera y lo ocultamos en la vista.
            if "x_studio_tipo_cheque" in rec._fields and check.type:
                selection = rec._fields["x_studio_tipo_cheque"].selection
                if callable(selection):
                    selection = selection(rec)
                possible_keys = [key for key, label in selection]
                if check.type == "echeq":
                    preferred = ("echeq", "e-check", "e-cheq", "e_cheq", "electronic", "electronico")
                else:
                    preferred = ("fisico", "físico", "physical")
                selected_key = next((key for key in preferred if key in possible_keys), False)
                if not selected_key:
                    # Fallback por etiqueta, útil si Studio creó claves distintas.
                    label_haystack = {
                        key: str(label).lower().replace("í", "i")
                        for key, label in selection
                    }
                    if check.type == "echeq":
                        selected_key = next(
                            (key for key, label in label_haystack.items() if "e" in label and "cheq" in label),
                            False,
                        )
                    else:
                        selected_key = next(
                            (key for key, label in label_haystack.items() if "fis" in label),
                            False,
                        )
                if selected_key:
                    vals["x_studio_tipo_cheque"] = selected_key

            if vals:
                rec.update(vals)

    @api.onchange("dflex_check_id")
    def _onchange_dflex_check_id(self):
        self._dflex_sync_from_selected_check()

    @api.model_create_multi
    def create(self, vals_list):
        checks = super().create(vals_list)
        checks._dflex_sync_from_selected_check()
        return checks

    def write(self, vals):
        res = super().write(vals)
        if "dflex_check_id" in vals:
            self._dflex_sync_from_selected_check()
        return res
