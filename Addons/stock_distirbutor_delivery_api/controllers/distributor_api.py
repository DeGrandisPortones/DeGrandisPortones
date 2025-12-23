# -*- coding: utf-8 -*-
from odoo import http, fields
from odoo.http import request
import json
import logging

_logger = logging.getLogger(__name__)


class DistributorApiController(http.Controller):
    """
    API para app de distribuidores.

    Endpoints expuestos (todos pensados para usarse via JS desde un front externo):
      - GET  /distributor/api/pickings
      - POST /distributor/api/pickings/<id>/final_customer
      - GET  /distributor/api/distributors
      - GET  /distributor/api/products
      - POST /distributor/api/quotations

    Todas las respuestas son JSON del tipo {"data": ...} o {"error": "..."}.
    """

    # -------------------------------------------------------------------------
    # Utilidades internas (CORS / JSON helpers)
    # -------------------------------------------------------------------------

    def _cors_headers(self):
        """Construye los headers CORS que se reutilizan en todas las respuestas."""
        origin = request.httprequest.headers.get("Origin") or "*"
        return [
            ("Access-Control-Allow-Origin", origin),
            ("Access-Control-Allow-Credentials", "true"),
            ("Access-Control-Allow-Methods", "GET, POST, OPTIONS"),
            (
                "Access-Control-Allow-Headers",
                "Origin, Content-Type, Accept, Authorization",
            ),
        ]

    def _json_default(self, obj):
        """Soporte para serializar datetime.date/datetime en JSON."""
        if hasattr(obj, "isoformat"):
            return obj.isoformat()
        return str(obj)

    def _json_response(self, payload, status=200):
        """Devuelve una respuesta JSON con CORS."""
        body = json.dumps(payload, default=self._json_default, ensure_ascii=False)
        headers = [("Content-Type", "application/json; charset=utf-8")]
        headers += self._cors_headers()
        response = request.make_response(body, headers)
        response.status_code = status
        return response

    def _handle_preflight(self):
        """Responde OK para las solicitudes OPTIONS (preflight CORS)."""
        if request.httprequest.method == "OPTIONS":
            return self._json_response({"ok": True}, status=200)
        return None

    # -------------------------------------------------------------------------
    # Helpers de negocio
    # -------------------------------------------------------------------------

    def _get_distributor_tag(self):
        """Etiqueta 'Distribuidor' en contactos."""
        Category = request.env["res.partner.category"].sudo()
        return Category.search([("name", "=", "Distribuidor")], limit=1)

    def _get_vip_pricelist(self):
        """
        Devuelve la lista de precios 'Lista Vip'.

        NO filtramos por compañía para evitar problemas de nombre de empresa.
        Se toma la primera que coincida por nombre.
        """
        Pricelist = request.env["product.pricelist"].sudo()
        return Pricelist.search([("name", "=", "Lista Vip")], limit=1)

    # -------------------------------------------------------------------------
    # Listado de entregas (pickings)
    # -------------------------------------------------------------------------

    @http.route(
        "/distributor/api/pickings",
        type="http",
        auth="public",
        methods=["GET", "OPTIONS"],
        csrf=False,
    )
    def list_pickings(self, **kwargs):
        """
        Devuelve los remitos de salida del día (y próximos) para distribuidores.

        Criterios:
          - picking_type_id.code = 'outgoing'
          - state in ('confirmed', 'assigned')
          - partner_id con etiqueta 'Distribuidor'
        """
        preflight = self._handle_preflight()
        if preflight:
            return preflight

        env = request.env
        StockPicking = env["stock.picking"].sudo()
        PartnerCategory = env["res.partner.category"].sudo()

        distributor_tag = self._get_distributor_tag()
        if not distributor_tag:
            _logger.warning("No existe la etiqueta 'Distribuidor' en res.partner.category")
            return self._json_response({"data": []})

        domain = [
            ("picking_type_id.code", "=", "outgoing"),
            ("state", "in", ["confirmed", "assigned"]),
            ("partner_id.category_id", "in", distributor_tag.ids),
        ]

        pickings = StockPicking.search(domain, order="scheduled_date asc, id desc")

        data = []
        for picking in pickings:
            lines = []
            for move in picking.move_ids_without_package:
                product = move.product_id
                if not product:
                    continue
                qty = move.product_uom_qty
                if qty <= 0:
                    continue

                lines.append(
                    {
                        "id": move.id,
                        "product_id": product.id,
                        "product_name": product.display_name,
                        "quantity": qty,
                        "uom": move.product_uom.name or "",
                    }
                )

            data.append(
                {
                    "id": picking.id,
                    "name": picking.name,
                    "origin": picking.origin or "",
                    "partner_name": picking.partner_id.name or "",
                    "scheduled_date": fields.Datetime.to_string(picking.scheduled_date)
                    if picking.scheduled_date
                    else None,
                    "state": picking.state,
                    "final_customer_completed": bool(
                        getattr(picking, "final_customer_completed", False)
                    ),
                    "final_customer_name": getattr(picking, "final_customer_name", "") or "",
                    "lines": lines,
                }
            )

        return self._json_response({"data": data})

    # -------------------------------------------------------------------------
    # Guardar datos del cliente final en el picking
    # -------------------------------------------------------------------------

    @http.route(
        "/distributor/api/pickings/<int:picking_id>/final_customer",
        type="http",
        auth="public",
        methods=["POST", "OPTIONS"],
        csrf=False,
    )
    def set_final_customer(self, picking_id, **kwargs):
        """
        Actualiza los campos de cliente final del picking
        (nombre, dirección, contacto, etc.) y marca final_customer_completed.
        """
        preflight = self._handle_preflight()
        if preflight:
            return preflight

        StockPicking = request.env["stock.picking"].sudo()

        picking = StockPicking.browse(picking_id)
        if not picking.exists():
            return self._json_response(
                {"error": "Picking no encontrado"}, status=404
            )

        # Leer JSON del body
        try:
            raw = request.httprequest.data or b"{}"
            payload = json.loads(raw.decode("utf-8"))
        except Exception as exc:
            _logger.exception("Error parseando JSON de final_customer: %s", exc)
            return self._json_response(
                {"error": "JSON inválido en el cuerpo de la petición"}, status=400
            )

        vals = {
            "final_customer_name": payload.get("name"),
            "final_customer_street": payload.get("street"),
            "final_customer_city": payload.get("city"),
            "final_customer_vat": payload.get("vat"),
            "final_customer_phone": payload.get("phone"),
            "final_customer_email": payload.get("email"),
            "final_customer_notes": payload.get("notes"),
            "final_customer_completed": True,
        }

        picking.write(vals)

        return self._json_response({"data": {"id": picking.id, "updated": True}})

    # -------------------------------------------------------------------------
    # Listado de distribuidores (contactos)
    # -------------------------------------------------------------------------

    @http.route(
        "/distributor/api/distributors",
        type="http",
        auth="public",
        methods=["GET", "OPTIONS"],
        csrf=False,
    )
    def list_distributors(self, **kwargs):
        """
        Devuelve los contactos marcados como 'Distribuidor'.

        Criterios:
          - active = True
          - categoría (etiqueta) 'Distribuidor'
        """
        preflight = self._handle_preflight()
        if preflight:
            return preflight

        env = request.env
        Partner = env["res.partner"].sudo()

        distributor_tag = self._get_distributor_tag()
        if not distributor_tag:
            _logger.warning("No existe la etiqueta 'Distribuidor' para listar distribuidores")
            return self._json_response({"data": []})

        domain = [
            ("active", "=", True),
            ("category_id", "in", distributor_tag.ids),
        ]

        partners = Partner.search(domain, order="name asc")

        data = []
        for partner in partners:
            data.append(
                {
                    "id": partner.id,
                    "name": partner.name,
                    "vat": partner.vat or "",
                    "street": partner.street or "",
                    "city": partner.city or "",
                    "phone": partner.phone or "",
                    "email": partner.email or "",
                }
            )

        return self._json_response({"data": data})

    # -------------------------------------------------------------------------
    # Productos de la lista de precios VIP
    # -------------------------------------------------------------------------

    @http.route(
        "/distributor/api/products",
        type="http",
        auth="public",
        methods=["GET", "OPTIONS"],
        csrf=False,
    )
    def list_products(self, **kwargs):
        """
        Devuelve SOLO los productos que tienen precio explícito
        en la lista de precios 'Lista Vip'.

        Para cada producto se envía:
          - id
          - name
          - default_code
          - uom_name
          - list_price  (precio de la lista VIP)
        """
        preflight = self._handle_preflight()
        if preflight:
            return preflight

        env = request.env
        PricelistItem = env["product.pricelist.item"].sudo()
        ProductProduct = env["product.product"].sudo()

        pricelist = self._get_vip_pricelist()
        if not pricelist:
            _logger.warning("No se encontró la lista de precios 'Lista Vip'")
            return self._json_response({"data": []})

        # Ítems de tarifa que aplican a productos concretos
        items = PricelistItem.search(
            [
                ("pricelist_id", "=", pricelist.id),
                ("applied_on", "in", ["0_product_variant", "1_product"]),
            ]
        )

        if not items:
            return self._json_response({"data": []})

        product_ids = set()
        price_by_product = {}

        for item in items:
            # Línea a nivel de variante
            if item.product_id:
                prod = item.product_id
                product_ids.add(prod.id)
                price = item.fixed_price if item.fixed_price not in (False, None) else prod.list_price
                price_by_product[prod.id] = float(price or 0.0)
            # Línea a nivel de plantilla: se aplica a todas las variantes
            elif item.product_tmpl_id:
                for prod in item.product_tmpl_id.product_variant_ids:
                    product_ids.add(prod.id)
                    price = item.fixed_price if item.fixed_price not in (False, None) else prod.list_price
                    price_by_product[prod.id] = float(price or 0.0)

        if not product_ids:
            return self._json_response({"data": []})

        products = ProductProduct.search(
            [
                ("id", "in", list(product_ids)),
                ("sale_ok", "=", True),
            ],
            order="name asc",
        )

        data = []
        for product in products:
            price = price_by_product.get(product.id, float(product.list_price or 0.0))
            data.append(
                {
                    "id": product.id,
                    "name": product.display_name,
                    "default_code": product.default_code or "",
                    "uom_name": product.uom_id.name or "",
                    "list_price": price,
                }
            )

        return self._json_response({"data": data})

    # -------------------------------------------------------------------------
    # Crear presupuesto (sale.order) para un distribuidor
    # -------------------------------------------------------------------------

    @http.route(
        "/distributor/api/quotations",
        type="http",
        auth="public",
        methods=["POST", "OPTIONS"],
        csrf=False,
    )
    def create_quotation(self, **kwargs):
        """
        Crea un sale.order para un distribuidor usando la lista
        de precios 'Lista Vip'.

        Request JSON:
        {
          "distributor_id": <id de res.partner con etiqueta Distribuidor>,
          "customer": {
            "name": "...",
            "phone": "...",
            "email": "...",
            "street": "...",
            "city": "..."
          },
          "notes": "texto libre",
          "lines": [
            {"product_id": 123, "quantity": 2, "price": 1000.0}, ...
          ]
        }
        """
        preflight = self._handle_preflight()
        if preflight:
            return preflight

        env = request.env
        Partner = env["res.partner"].sudo()
        SaleOrder = env["sale.order"].sudo()
        SaleOrderLine = env["sale.order.line"].sudo()
        ProductProduct = env["product.product"].sudo()

        # Leer y validar body JSON
        try:
            raw = request.httprequest.data or b"{}"
            payload = json.loads(raw.decode("utf-8"))
        except Exception as exc:
            _logger.exception("Error parseando JSON de create_quotation: %s", exc)
            return self._json_response(
                {"error": "JSON inválido en el cuerpo de la petición"}, status=400
            )

        distributor_id = payload.get("distributor_id")
        customer = payload.get("customer") or {}
        notes = payload.get("notes") or ""
        lines = payload.get("lines") or []

        if not distributor_id:
            return self._json_response(
                {"error": "Falta distributor_id en el pedido"}, status=400
            )

        distributor = Partner.browse(int(distributor_id))
        if not distributor.exists():
            return self._json_response(
                {"error": "Distribuidor no encontrado"}, status=404
            )

        if not lines:
            return self._json_response(
                {"error": "Debe enviar al menos una línea de producto"}, status=400
            )

        pricelist = self._get_vip_pricelist()
        if not pricelist:
            return self._json_response(
                {"error": "No se encontró la lista de precios 'Lista Vip'"},
                status=400,
            )

        # Armamos nota interna con datos del cliente final
        customer_name = customer.get("name") or ""
        customer_phone = customer.get("phone") or ""
        customer_email = customer.get("email") or ""
        customer_street = customer.get("street") or ""
        customer_city = customer.get("city") or ""

        note_lines = []
        if customer_name:
            note_lines.append("Cliente final: %s" % customer_name)
        if customer_phone:
            note_lines.append("Teléfono: %s" % customer_phone)
        if customer_email:
            note_lines.append("Email: %s" % customer_email)
        if customer_street or customer_city:
            note_lines.append("Dirección: %s %s" % (customer_street, customer_city))
        if notes:
            note_lines.append("")
            note_lines.append("Notas distribuidor:")
            note_lines.append(notes)

        internal_note = "\n".join(note_lines)

        # Crear presupuesto
        order_vals = {
            "partner_id": distributor.id,
            "partner_invoice_id": distributor.id,
            "partner_shipping_id": distributor.id,
            "pricelist_id": pricelist.id,
            "note": internal_note,
        }

        order = SaleOrder.create(order_vals)

        for line in lines:
            product_id = line.get("product_id")
            qty = line.get("quantity") or 0.0
            price = line.get("price")  # viene desde el front, calculado con la VIP

            if not product_id or qty <= 0:
                continue

            product = ProductProduct.browse(int(product_id))
            if not product.exists():
                continue

            # Si no viene precio desde el front, usamos el de la lista VIP
            if price in (None, False):
                item = pricelist.item_ids.filtered(
                    lambda i: i.product_id == product
                    or i.product_tmpl_id == product.product_tmpl_id
                )[:1]
                if item and item.fixed_price not in (False, None):
                    price = item.fixed_price
                else:
                    price = product.list_price

            line_vals = {
                "order_id": order.id,
                "product_id": product.id,
                "product_uom_qty": qty,
                "price_unit": float(price or 0.0),
            }
            SaleOrderLine.create(line_vals)

        return self._json_response(
            {
                "data": {
                    "order_id": order.id,
                    "name": order.name,
                }
            },
            status=200,
        )
