from odoo import api, fields, models, _
from odoo.exceptions import UserError


class DflexPortonWorkflow(models.Model):
    _name = "dflex.porton.workflow"
    _description = "Workflow para portones"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    name = fields.Char(
        string="Referencia",
        required=True,
        copy=False,
        default=lambda self: _("Nuevo"),
        tracking=True,
    )

    porton_id = fields.Many2one(
        "x_dflex.porton",
        string="Portón",
        required=True,
        tracking=True,
    )

    sale_id = fields.Many2one(
        "sale.order",
        string="Cotización / Pedido",
        required=True,
        tracking=True,
    )

    company_id = fields.Many2one(
        "res.company",
        string="Compañía",
        required=True,
        default=lambda self: self.env.company,
    )

    # Estados generales
    state = fields.Selection(
        [
            ("draft", "Borrador"),
            ("acopio", "Acopio"),
            ("pend_medicion", "Pendiente de medición"),
            ("pend_mod_comercial", "Pendiente ajustes comerciales"),
            ("pre_produccion", "Pre-producción"),
            ("aprobado", "Aprobado para producción"),
            ("produccion", "En producción"),
            ("done", "Listo"),
            ("cancel", "Cancelado"),
        ],
        string="Estado",
        default="draft",
        tracking=True,
    )

    # Flags de origen / flujo
    es_distribuidor = fields.Boolean(
        string="Venta vía distribuidor",
        help="Si está tildado, se asume que ya hay medidas finales y "
             "el portón puede ir a pre-producción directo.",
    )
    necesita_medicion = fields.Boolean(
        string="Requiere medición en obra",
        help="Si está tildado, pasa por el estado 'Pendiente de medición'.",
    )

    # Datos de medición
    fecha_medicion = fields.Date(string="Fecha de medición")
    usuario_medicion_id = fields.Many2one(
        "res.users",
        string="Usuario que midió",
    )

    # Autorizaciones
    aprob_comercial_uid = fields.Many2one(
        "res.users",
        string="Aprobado por Comercial",
        readonly=True,
        copy=False,
    )
    aprob_planif_uid = fields.Many2one(
        "res.users",
        string="Aprobado por Planificación",
        readonly=True,
        copy=False,
    )
    aprob_admin_uid = fields.Many2one(
        "res.users",
        string="Aprobado por Administración",
        readonly=True,
        copy=False,
    )

    aprob_comercial_date = fields.Datetime(
        string="Fecha aprobación Comercial",
        readonly=True,
        copy=False,
    )
    aprob_planif_date = fields.Datetime(
        string="Fecha aprobación Planificación",
        readonly=True,
        copy=False,
    )
    aprob_admin_date = fields.Datetime(
        string="Fecha aprobación Administración",
        readonly=True,
        copy=False,
    )

    # MRP
    production_id = fields.Many2one(
        "mrp.production",
        string="Orden de Producción",
        readonly=True,
        copy=False,
    )

    # Campos auxiliares
    notes = fields.Text(string="Notas internas")

    @api.model
    def create(self, vals):
        if vals.get("name", _("Nuevo")) == _("Nuevo"):
            vals["name"] = self.env["ir.sequence"].next_by_code("dflex.porton.workflow") or _("Nuevo")
        return super().create(vals)

    # ======================
    # Acciones de estado
    # ======================

    def action_set_acopio(self):
        for rec in self:
            rec.state = "acopio"

    def action_set_pend_medicion(self):
        for rec in self:
            if not rec.necesita_medicion:
                raise UserError(_("Este portón no está marcado como 'Requiere medición en obra'."))
            rec.state = "pend_medicion"

    def action_set_pend_mod_comercial(self):
        for rec in self:
            rec.state = "pend_mod_comercial"

    def action_set_pre_produccion(self):
        for rec in self:
            rec.state = "pre_produccion"

    # Aprobaciones
    def action_aprobar_comercial(self):
        self._check_user_in_group("dflex_portones_workflow.group_dflex_comercial")
        for rec in self:
            rec.aprob_comercial_uid = self.env.user
            rec.aprob_comercial_date = fields.Datetime.now()
            rec._check_si_todas_aprobaciones()

    def action_aprobar_planificacion(self):
        self._check_user_in_group("dflex_portones_workflow.group_dflex_planificacion")
        for rec in self:
            rec.aprob_planif_uid = self.env.user
            rec.aprob_planif_date = fields.Datetime.now()
            rec._check_si_todas_aprobaciones()

    def action_aprobar_administracion(self):
        self._check_user_in_group("dflex_portones_workflow.group_dflex_administracion")
        for rec in self:
            rec.aprob_admin_uid = self.env.user
            rec.aprob_admin_date = fields.Datetime.now()
            rec._check_si_todas_aprobaciones()

    def _check_user_in_group(self, xmlid_group):
        """Valida que el usuario actual pertenezca al grupo indicado."""
        if not self.env.user.has_group(xmlid_group):
            raise UserError(_("No tiene permisos para realizar esta acción."))

    def _check_si_todas_aprobaciones(self):
        """Si las 3 aprobaciones están dadas, pasa a estado 'aprobado'."""
        for rec in self:
            if rec.aprob_comercial_uid and rec.aprob_planif_uid and rec.aprob_admin_uid:
                rec.state = "aprobado"

    # Creación de MO (simplificada)
    def action_crear_orden_produccion(self):
        """Crea una orden de producción básica desde el portón."""
        for rec in self:
            if rec.state != "aprobado":
                raise UserError(_("El portón debe estar en estado 'Aprobado para producción'."))

            if not rec.sale_id:
                raise UserError(_("No hay cotización / pedido vinculado."))

            if rec.production_id:
                raise UserError(_("Ya existe una orden de producción vinculada."))

            # Extra simple: tomamos el primer product_id de la cotización
            line = rec.sale_id.order_line[:1]
            if not line:
                raise UserError(_("La cotización no tiene líneas de producto."))

            product = line.product_id
            if not product:
                raise UserError(_("La primera línea de la cotización no tiene producto seteado."))

            values = {
                "product_id": product.id,
                "product_qty": line.product_uom_qty,
                "product_uom_id": product.uom_id.id,
                "origin": rec.sale_id.name,
                "company_id": rec.company_id.id,
            }
            mo = self.env["mrp.production"].create(values)
            rec.production_id = mo.id
            rec.state = "produccion"