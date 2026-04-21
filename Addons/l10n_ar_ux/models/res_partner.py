import logging

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.http import request

_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    _inherit = "res.partner"

    gross_income_jurisdiction_ids = fields.Many2many(
        "res.country.state",
        string="Gross Income Jurisdictions",
        help="The state of the company is cosidered the main jurisdiction",
    )

    # AFIP Padron
    start_date = fields.Date("Activities Start")
    estado_padron = fields.Char("Estado AFIP")
    imp_ganancias_padron = fields.Selection(
        [("NI", "No Inscripto"), ("AC", "Activo"), ("EX", "Exento"), ("NC", "No corresponde")], "Ganancias"
    )
    imp_iva_padron = fields.Selection(
        [
            ("NI", "No Inscripto"),
            ("AC", "Activo"),
            ("EX", "Exento"),
            ("NA", "No alcanzado"),
            ("XN", "Exento no alcanzado"),
            ("AN", "Activo no alcanzado"),
        ],
        "IVA",
    )
    integrante_soc_padron = fields.Selection([("N", "No"), ("S", "Si")], "Integrante Sociedad")
    monotributo_padron = fields.Selection([("N", "No"), ("S", "Si")], "Monotributo")
    actividad_monotributo_padron = fields.Char()
    empleador_padron = fields.Boolean()
    actividades_padron = fields.Many2many(
        "afip.activity",
        "res_partner_afip_activity_rel",
        "partner_id",
        "afip_activity_id",
        "Actividades",
    )
    impuestos_padron = fields.Many2many(
        "afip.tax", "res_partner_afip_tax_rel", "partner_id", "afip_tax_id", "Impuestos"
    )
    last_update_padron = fields.Date()

    _invoice_edit_protected_fields = {
        "name",
        "vat",
        "street",
        "street2",
        "zip",
        "city",
        "state_id",
        "country_id",
        "phone",
        "mobile",
        "email",
        "website",
        "l10n_latam_identification_type_id",
        "l10n_ar_afip_responsibility_type_id",
    }

    @api.constrains("gross_income_jurisdiction_ids", "state_id")
    def check_gross_income_jurisdictions(self):
        for rec in self:
            if rec.state_id and rec.state_id in rec.gross_income_jurisdiction_ids:
                raise ValidationError(
                    _(
                        "Jurisdiction %s is considered the main jurisdiction "
                        "because it is the state of the company, please remove it "
                        "from the jurisdiction list"
                    )
                    % rec.state_id.name
                )

    def _get_invoice_edit_changed_field_labels(self, vals):
        field_labels = []
        for field_name in sorted(self._invoice_edit_protected_fields & set(vals.keys())):
            field = self._fields.get(field_name)
            if field:
                field_labels.append(field.string or field_name)
            else:
                field_labels.append(field_name)
        return field_labels

    def _get_invoice_edit_blocking_move(self, commercial_partner):
        return self.env["account.move"].sudo().search(
            [
                ("partner_id", "child_of", commercial_partner.id),
                (
                    "move_type",
                    "in",
                    [
                        "out_invoice",
                        "out_refund",
                        "out_receipt",
                        "in_invoice",
                        "in_refund",
                        "in_receipt",
                    ],
                ),
                ("state", "!=", "cancel"),
            ],
            order="invoice_date desc, date desc, id desc",
            limit=1,
        )

    def _get_invoice_edit_move_type_label(self, move):
        move_type_labels = {
            "out_invoice": _("Factura de cliente"),
            "out_refund": _("Nota de crédito de cliente"),
            "out_receipt": _("Recibo de cliente"),
            "in_invoice": _("Factura de proveedor"),
            "in_refund": _("Nota de crédito de proveedor"),
            "in_receipt": _("Recibo de proveedor"),
        }
        return move_type_labels.get(move.move_type, move.move_type or "-")

    def _get_invoice_edit_state_label(self, move):
        state_labels = {
            "draft": _("Borrador"),
            "posted": _("Publicado"),
            "cancel": _("Cancelado"),
        }
        return state_labels.get(move.state, move.state or "-")

    def _raise_invoice_edit_validation(self, commercial_partner, changed_fields, blocking_move):
        field_lines = "\n- ".join(changed_fields) if changed_fields else _("Sin detalle")
        partner_role = (
            _("Cliente") if blocking_move.move_type in ["out_invoice", "out_refund", "out_receipt"] else _("Proveedor")
        )
        move_number = blocking_move.name or blocking_move.ref or _("Sin número")
        move_date = fields.Date.to_string(blocking_move.invoice_date or blocking_move.date) or "-"

        raise ValidationError(
            _(
                "No podés modificar los datos del contacto '%(partner)s' porque ya tiene comprobantes asociados.\n\n"
                "Campos que intentás modificar:\n"
                "- %(fields)s\n\n"
                "Comprobante detectado:\n"
                "- Tipo: %(move_type)s\n"
                "- Número: %(move_number)s\n"
                "- Fecha: %(move_date)s\n"
                "- Estado: %(move_state)s\n"
                "- %(partner_role)s: %(commercial_partner)s"
            )
            % {
                "partner": commercial_partner.display_name,
                "fields": field_lines,
                "move_type": self._get_invoice_edit_move_type_label(blocking_move),
                "move_number": move_number,
                "move_date": move_date,
                "move_state": self._get_invoice_edit_state_label(blocking_move),
                "partner_role": partner_role,
                "commercial_partner": commercial_partner.display_name,
            }
        )

    def write(self, vals):
        if self.env.context.get("skip_partner_invoice_edit_check"):
            return super().write(vals)

        changed_fields = self._get_invoice_edit_changed_field_labels(vals)
        if not changed_fields:
            return super().write(vals)

        if self.env.user.has_group("sales_team.group_sale_salesman"):
            for partner in self:
                commercial_partner = partner.commercial_partner_id
                blocking_move = self._get_invoice_edit_blocking_move(commercial_partner)
                if blocking_move:
                    self._raise_invoice_edit_validation(commercial_partner, changed_fields, blocking_move)

        return super().write(vals)

    @api.model
    def try_write_commercial(self, data):
        """User for website. capture the validation errors and return them.
        return (error, error_message) = (dict[fields], list(str()))"""
        error = dict()
        error_message = []
        vat = data.get("vat")
        l10n_latam_identification_type_id = data.get("l10n_latam_identification_type_id")
        l10n_ar_afip_responsibility_type_id = data.get("l10n_ar_afip_responsibility_type_id", False)

        if vat and l10n_latam_identification_type_id:
            commercial_partner = request.env.user.partner_id.commercial_partner_id
            try:
                values = {
                    "vat": vat,
                    "l10n_latam_identification_type_id": int(l10n_latam_identification_type_id),
                    "l10n_ar_afip_responsibility_type_id": int(l10n_ar_afip_responsibility_type_id)
                    if l10n_ar_afip_responsibility_type_id
                    else False,
                }
                commercial_fields = ["vat", "l10n_latam_identification_type_id", "l10n_ar_afip_responsibility_type_id"]
                values = commercial_partner.remove_readonly_required_fields(commercial_fields, values)
                with self.env.cr.savepoint():
                    commercial_partner.write(values)
            except Exception as exception_error:
                _logger.error(exception_error)
                error["vat"] = "error"
                error["l10n_latam_identification_type_id"] = "error"
                error_message.append(_(exception_error))
        return error, error_message

    def remove_readonly_required_fields(self, required_fields, values):
        """In some cases we have information showed to the user in the for that is required but that is already set
        and readonly. We do not really update this fields and then here we are trying to write them: the problem is
        that this fields has a constraint if we are trying to re-write them (even when is the same value).

        This method remove this (field, values) for the values to write in order to do avoid the constraint and not
        re-writted again when they has been already writted.

        param: @required_fields: (list) fields of the fields that we want to check
        param: @values (dict) the values of the web form

        return: the same values to write and they do not include required/readonly fields.
        """
        self.ensure_one()
        for r_field in required_fields:
            value = values.get(r_field)
            if r_field.endswith("_id"):
                if self[r_field].id == value:
                    values.pop(r_field, False)
            else:
                if self[r_field] == value:
                    values.pop(r_field, False)
        return values

    @api.onchange("vat", "country_id", "l10n_latam_identification_type_id")
    def _onchange_ar_identification_fields(self):
        """
        Agregamos este onchange para que cuando el usuario modifique el VAT o el tipo de documento
        se formatee el VAT automaticamente si es un CUIT o un DNI.
        En v19 esto ya está hecho en este commit https://github.com/odoo/odoo/commit/ac95d2d6d80a368dfb190d0ac21da2af479a8488.
        Traemos sólo lo necesario acá para tenerlo disponible en esta versión.
        """
        l10n_ar_partners = self.filtered(
            lambda p: p.vat and (p.l10n_latam_identification_type_id.l10n_ar_afip_code or p.country_code == "AR")
        )
        for partner in l10n_ar_partners:
            if id_number := partner._get_id_number_sanitize():
                partner.vat = str(id_number)
