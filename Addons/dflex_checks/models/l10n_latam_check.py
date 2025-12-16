from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class L10nLatamCheck(models.Model):
    _inherit = "l10n_latam.check"

    # Vínculo interno al cheque en cartera (DFlex)
    dflex_check_id = fields.Many2one(
        "dflex.check",
        string="Cheque en cartera (DFlex)",
        compute="_compute_dflex_check_id",
        store=True,
        readonly=True,
        copy=False,
    )
    dflex_check_state = fields.Selection(
        related="dflex_check_id.state",
        string="Estado de emisión",
        store=True,
        readonly=True,
    )

    @api.depends("name", "payment_id", "payment_id.journal_id", "payment_id.journal_id.bank_account_id")
    def _compute_dflex_check_id(self):
        """Vincula automáticamente el cheque de DFlex a partir del número (campo 'name').

        Esto está pensado para el tablero estándar de 'Cheques' en pagos, donde el usuario carga el número.
        """
        Dflex = self.env["dflex.check"]
        for rec in self:
            rec.dflex_check_id = False
            if not rec.name:
                continue

            s = (rec.name or "").strip()
            if not s:
                continue

            # Base domain: compañía y banco (si se puede inferir del diario del pago)
            domain_base = [("company_id", "=", rec.company_id.id)] if "company_id" in rec._fields else []
            bank_id = False
            if getattr(rec, "payment_id", False) and rec.payment_id.journal_id:
                journal = rec.payment_id.journal_id
                bank_id = journal.bank_account_id.bank_id.id if journal.bank_account_id and journal.bank_account_id.bank_id else False
            if bank_id:
                domain_base.append(("bank_id", "=", bank_id))

            # Si es numérico, matchear por número (integer). Si no, por name (char).
            matches = Dflex.browse()
            if s.isdigit():
                num = int(s)
                matches = Dflex.search(domain_base + [("number", "=", num)], limit=2)
            else:
                matches = Dflex.search(domain_base + [("name", "=", s)], limit=2)

            # Solo autovincular si hay unívoco.
            if len(matches) == 1:
                rec.dflex_check_id = matches.id

    @api.constrains("name", "payment_id")
    def _check_dflex_check_unique_and_available(self):
        """Valida que el número ingresado corresponda a un cheque en cartera disponible (DFlex)."""
        Dflex = self.env["dflex.check"]
        for rec in self:
            if not rec.name:
                continue
            s = (rec.name or "").strip()
            if not s or not s.isdigit():
                # Si no es numérico, no forzamos validación (evita romper otros usos del modelo).
                continue

            num = int(s)

            # Base domain: compañía y banco (según diario del pago) para evitar cruces.
            domain_base = [("company_id", "=", rec.company_id.id)] if "company_id" in rec._fields else []
            bank_id = False
            if getattr(rec, "payment_id", False) and rec.payment_id.journal_id:
                journal = rec.payment_id.journal_id
                bank_id = journal.bank_account_id.bank_id.id if journal.bank_account_id and journal.bank_account_id.bank_id else False
            if bank_id:
                domain_base.append(("bank_id", "=", bank_id))

            all_matches = Dflex.search(domain_base + [("number", "=", num)])
            if not all_matches:
                raise ValidationError(
                    _("No existe un cheque en cartera con número %(num)s para la compañía/banco del pago.")
                    % {"num": num}
                )

            available = all_matches.filtered(lambda c: c.state == "available")
            if not available:
                # Tomamos el primer match para informar estado
                chk = all_matches[0]
                selection = dict(chk._fields["state"].selection)
                raise ValidationError(
                    _("El cheque %(name)s no está disponible. Estado actual: %(state)s")
                    % {"name": chk.display_name, "state": selection.get(chk.state, chk.state)}
                )

            if len(available) > 1:
                raise ValidationError(
                    _("Hay más de un cheque disponible con el número %(num)s. Revisá duplicados en la cartera.")
                    % {"num": num}
                )

            # Setear el vínculo si aún no quedó computado (por orden de compute/constraint).
            if not rec.dflex_check_id:
                rec.dflex_check_id = available[0].id
