from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class DflexCheckbook(models.Model):
    _name = "dflex.checkbook"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "Chequera de cheques propios"
    _order = "id desc"

    name = fields.Char(string="Nombre", required=True, default=lambda self: _("Chequera"))
    bank_id = fields.Many2one("res.bank", string="Banco", required=True)
    type = fields.Selection(
        [("fisico", "Físico"), ("echeq", "eCheq")],
        string="Tipo",
        required=True,
        default="fisico",
    )

    start_number = fields.Integer(string="Número inicial", required=True)
    quantity = fields.Integer(string="Cantidad de cheques", required=True)
    last_number = fields.Integer(string="Último número", compute="_compute_last_number", store=True)

    company_id = fields.Many2one(
        "res.company", string="Compañía", default=lambda self: self.env.company, required=True
    )
    state = fields.Selection(
        [("draft", "Borrador"), ("generated", "Generada"), ("closed", "Cerrada")],
        default="draft",
        string="Estado",
        tracking=True,
    )

    check_ids = fields.One2many("dflex.check", "checkbook_id", string="Cheques")

    _sql_constraints = [
        (
            "start_positive",
            "CHECK(start_number > 0 AND quantity > 0)",
            "El número inicial y la cantidad deben ser positivos.",
        ),
    ]

    @api.depends("start_number", "quantity")
    def _compute_last_number(self):
        for rec in self:
            rec.last_number = rec.start_number + rec.quantity - 1 if rec.quantity and rec.start_number else 0

    def action_generate_checks(self):
        for book in self:
            if book.state != "draft":
                raise ValidationError(_("Solo se pueden generar cheques desde el estado Borrador."))

            # Validar solapamientos con otras chequeras del mismo banco/empresa
            overlap = self.search(
                [
                    ("id", "!=", book.id),
                    ("bank_id", "=", book.bank_id.id),
                    ("company_id", "=", book.company_id.id),
                    ("start_number", "<=", book.last_number),
                    ("last_number", ">=", book.start_number),
                ],
                limit=1,
            )
            if overlap:
                raise ValidationError(
                    _("El rango de esta chequera se solapa con otra existente (%s).") % overlap.display_name
                )

            vals_list = []
            for number in range(book.start_number, book.last_number + 1):
                vals_list.append(
                    {
                        "name": str(number),
                        "number": number,
                        "bank_id": book.bank_id.id,
                        "type": book.type,
                        "company_id": book.company_id.id,
                        "checkbook_id": book.id,
                    }
                )
            self.env["dflex.check"].create(vals_list)
            book.state = "generated"

    def action_close(self):
        for book in self:
            book.state = "closed"
