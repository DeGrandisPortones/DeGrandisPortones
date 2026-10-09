# -*- coding: utf-8 -*-
import re

from odoo import api, fields, models

# "Cerco Vert PREMIUM 1.50 Alto por 5 metros lineales" -> alto "1.50", largo "5"
_ROLLO_RE = re.compile(
    r"(\d+(?:[.,]\d+)?)\s*(?:m\s+)?alto\s+por\s+(\d+(?:[.,]\d+)?)\s*metros?\s+lineales",
    re.IGNORECASE,
)
# Referencia interna al principio de la descripción: "[1982289966] Cerco ..."
_REFERENCIA_RE = re.compile(r"^\[[^\]]*\]\s*")


class SaleOrder(models.Model):
    _inherit = "sale.order"

    dg_datos_envio_text = fields.Text(
        string="Datos de envío",
        compute="_compute_dg_datos_envio_text",
        help="Datos del cliente y de la entrega para pegar en WhatsApp al "
        "coordinar el flete.",
    )

    @api.depends(
        "company_id.dg_datos_envio_enabled",
        "partner_id.name",
        "partner_id.vat",
        "partner_id.email",
        "partner_id.phone",
        "partner_id.mobile",
        "partner_shipping_id.name",
        "partner_shipping_id.street",
        "partner_shipping_id.street2",
        "partner_shipping_id.city",
        "partner_shipping_id.state_id",
        "partner_shipping_id.zip",
        "partner_shipping_id.country_id",
        "order_line.display_type",
        "order_line.product_id",
        "order_line.name",
        "order_line.product_uom_qty",
    )
    def _compute_dg_datos_envio_text(self):
        for order in self:
            if order.company_id.dg_datos_envio_enabled and order.partner_id:
                order.dg_datos_envio_text = order._dg_datos_envio_text()
            else:
                order.dg_datos_envio_text = False

    def _dg_datos_envio_text(self):
        self.ensure_one()
        cliente = self.partner_id
        entrega = self.partner_shipping_id or cliente

        telefonos = []
        for numero in (cliente.mobile, cliente.phone):
            if numero and numero not in telefonos:
                telefonos.append(numero)

        renglones = [
            f"Nombre completo: {cliente.name or cliente.commercial_partner_id.name or ''}",
            f"Cuit o DNI: {cliente.vat or ''}",
            f"mail: {cliente.email or ''}",
            f"Telefono: {' / '.join(telefonos)}",
            f"Dirección: {self._dg_direccion_entrega(entrega)}",
            f"Codigo Postal: {entrega.zip or ''}",
        ]
        cantidades = self._dg_cantidades_envio()
        if len(cantidades) == 1:
            renglones.append(f"Cantidad: {cantidades[0]}")
        else:
            renglones.append("Cantidad:")
            renglones.extend(f"- {cantidad}" for cantidad in cantidades)
        return "\n".join(renglones)

    def _dg_direccion_entrega(self, entrega):
        partes = []
        # Si se entrega en otra dirección (p. ej. una agencia de transporte),
        # su nombre le sirve al flete: "Agencia ViaCargo, Sarmiento 160, ..."
        if entrega != self.partner_id and entrega.name and entrega.name != self.partner_id.name:
            partes.append(entrega.name)
        partes += [entrega.street, entrega.street2, entrega.city, entrega.state_id.name]
        if entrega.country_id and entrega.country_id != self.company_id.country_id:
            partes.append(entrega.country_id.name)
        return ", ".join(parte.strip() for parte in partes if parte and parte.strip())

    def _dg_cantidades_envio(self):
        cantidades = []
        for line in self.order_line:
            # Solo bienes: quedan afuera secciones, notas (suelen tener las
            # condiciones de pago), descuentos, envíos y anticipos.
            if line.display_type or line.product_id.type != "consu" or not line.product_uom_qty:
                continue
            descripcion = (line.name or line.product_id.display_name or "").split("\n")[0]
            descripcion = _REFERENCIA_RE.sub("", descripcion).strip()
            cantidad = ("%.3f" % line.product_uom_qty).rstrip("0").rstrip(".")
            rollo = _ROLLO_RE.search(descripcion)
            if rollo:
                unidad = "rollo" if line.product_uom_qty == 1 else "rollos"
                cantidades.append(f"{cantidad} {unidad} de {rollo.group(1)} x {rollo.group(2)}")
            else:
                cantidades.append(f"{cantidad} x {descripcion}")
        return cantidades
