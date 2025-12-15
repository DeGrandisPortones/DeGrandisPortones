# stock_distirbutor_delivery_api/controllers/distributor_api.py
import json

from odoo import http
from odoo.http import request


class DistributorApiController(http.Controller):
    """API para distribuidor:
    - Entregas (stock.picking)
    - Pseudo-presupuestador (sale.order)
    """

    # ---------- Helper JSON + CORS ----------

    def _json_response(self, data, status=200):
        body = json.dumps(data, default=str)
        headers = [
            ("Content-Type", "application/json"),
            ("Access-Control-Allow-Origin", "*"),
            ("Access-Control-Allow-Methods", "GET, POST, OPTIONS"),
            ("Access-Control-Allow-Headers", "Content-Type, Authorization"),
        ]
        response = request.make_response(body, headers)
        response.status_code = status
        return response

    # ---------- Helpers de negocio ----------

    def _get_distributor_customers(self):
        """Clientes marcados para ser usados en la app del distribuidor."""
        Partner = request.env["res.partner"].sudo()
        return Partner.search([("distributor_customer", "=", True)], order="name")

    # ---------- API ENTREGAS (ya existente, con tu lógica) ----------

    @http.route(
        "/distributor/api/pickings",
        type="http",
        auth="public",  # user + API Key en Basic Auth
        methods=["GET", "OPTIONS"],
        csrf=False,
    )
    def list_pickings(self, **kwargs):
        """Devuelve las entregas pendientes para distribuidor."""
        if request.httprequest.method == "OPTIONS":
            return self._json_response({}, status=200)

        user = request.env.user

        Picking = request.env["stock.picking"].sudo().with_context(lang=user.lang)

        domain = [
            ("picking_type_id.code", "=", "outgoing"),
            ("state", "in", ["confirmed", "assigned"]),
            ("is_distributor_delivery", "=", True),
            ("final_customer_completed", "=", False),
        ]

        pickings = Picking.search(domain, order="scheduled_date, id")

        data = []
        for picking in pickings:
            line_data = []
            for move in picking.move_ids_without_package:
                line_data.append(
                    {
                        "id": move.id,
                        "product_name": move.product_id.display_name,
                        "quantity": move.quantity or move.product_uom_qty,
                        "uom": move.product_uom.name,
                    }
                )

            data.append(
                {
                    "id": picking.id,
                    "name": picking.name,
                    "origin": picking.origin,
                    "scheduled_date": picking.scheduled_date,
                    "state": picking.state,
                    "partner_name": picking.partner_id.name,
                    "partner_ref": picking.partner_id.ref,
                    "is_distributor_delivery": picking.is_distributor_delivery,
                    "final_customer_completed": picking.final_customer_completed,
                    "final_customer_name": picking.final_customer_name,
                    "lines": line_data,
                }
            )

        return self._json_response({"data": data})

    @http.route(
        "/distributor/api/pickings/<int:picking_id>/final_customer",
        type="http",
        auth="public",
        methods=["POST", "OPTIONS"],
        csrf=False,
    )
    def set_final_customer(self, picking_id, **kwargs):
        """Guarda los datos del cliente final para un picking concreto."""
        if request.httprequest.method == "OPTIONS":
            return self._json_response({}, status=200)

        user = request.env.user

        # Parsear JSON del body
        try:
            raw = request.httprequest.get_data()
            payload = json.loads(raw.decode("utf-8") or "{}")
        except Exception:
            return self._json_response(
                {"error": "Invalid JSON payload."},
                status=400,
            )

        Picking = request.env["stock.picking"].sudo().with_context(lang=user.lang)

        # Solo permitimos pickings marcados como 'Entrega vía distribuidor'
        picking = Picking.search(
            [
                ("id", "=", picking_id),
                ("is_distributor_delivery", "=", True),
            ],
            limit=1,
        )

        if not picking:
            return self._json_response(
                {"error": "Picking not found or not marked for distributor."},
                status=404,
            )

        values = {
            "final_customer_name": payload.get("name"),
            "final_customer_street": payload.get("street"),
            "final_customer_city": payload.get("city"),
            "final_customer_vat": payload.get("vat"),
            "final_customer_phone": payload.get("phone"),
            "final_customer_notes": payload.get("notes"),
            "final_customer_completed": True,
        }

        picking.write(values)

        return self._json_response(
            {
                "success": True,
                "picking_id": picking.id,
            }
        )

    # ---------- API PSEUDO-PRESUPUESTADOR ----------

    @http.route(
        "/distributor/api/presale/config",
        type="http",
        auth="public",
        methods=["GET", "OPTIONS"],
        csrf=False,
    )
    def presale_config(self, **kwargs):
        """
        Config general del pseudo-presupuestador:
        - clientes disponibles para el distribuidor
        - lista de precios de cada cliente
        """
        if request.httprequest.method == "OPTIONS":
            return self._json_response({}, status=200)

        user = request.env.user
        customers = self._get_distributor_customers().with_context(lang=user.lang)

        data = {
            "customers": [
                {
                    "id": partner.id,
                    "name": partner.display_name,
                    "pricelist_id": partner.property_product_pricelist.id
                    if partner.property_product_pricelist
                    else False,
                    "pricelist_name": partner.property_product_pricelist.name
                    if partner.property_product_pricelist
                    else "",
                }
                for partner in customers
            ]
        }
        return self._json_response(data)

    @http.route(
        "/distributor/api/products",
        type="http",
        auth="public",
        methods=["GET", "OPTIONS"],
        csrf=False,
    )
    def list_products(self, **kwargs):
        """
        Devuelve los productos disponibles para el pseudo-presupuestador.

        Query params:
        - customer_id (opcional): para calcular el precio según la lista del cliente.

        Dominio de productos:
        - sale_ok = True
        - active = True
        - distributor_available = True
        """
        if request.httprequest.method == "OPTIONS":
            return self._json_response({}, status=200)

        user = request.env.user
        Partner = request.env["res.partner"].sudo().with_context(lang=user.lang)
        Product = request.env["product.product"].sudo().with_context(lang=user.lang)

        customer_id = kwargs.get("customer_id")
        partner = None
        pricelist = None

        if customer_id:
            try:
                customer_id = int(customer_id)
            except ValueError:
                customer_id = 0
            if customer_id:
                partner = Partner.search([("id", "=", customer_id)], limit=1)
                if partner:
                    pricelist = partner.property_product_pricelist

        domain = [
            ("sale_ok", "=", True),
            ("active", "=", True),
            ("distributor_available", "=", True),
        ]
        products = Product.search(domain, order="name", limit=200)

        items = []
        for product in products:
            price = 0.0
            if pricelist and partner:
                price = pricelist._get_product_price(product, 1.0, partner)

            items.append(
                {
                    "id": product.id,
                    "name": product.display_name,
                    "default_code": product.default_code,
                    "uom": product.uom_id.name,
                    "price": price,
                }
            )

        return self._json_response({"products": items})

    @http.route(
        "/distributor/api/quotations",
        type="http",
        auth="public",
        methods=["POST", "OPTIONS"],
        csrf=False,
    )
    def create_quotation(self, **kwargs):
        """
        Crea una cotización (sale.order) para el distribuidor.

        Body:
        {
          "customer_id": 123,
          "lines": [
            {"product_id": 1, "quantity": 2},
            ...
          ],
          "notes": "texto opcional"
        }
        """
        if request.httprequest.method == "OPTIONS":
            return self._json_response({}, status=200)

        user = request.env.user

        # Parsear JSON
        try:
            raw = request.httprequest.get_data()
            payload = json.loads(raw.decode("utf-8") or "{}")
        except Exception:
            return self._json_response({"error": "Invalid JSON payload."}, status=400)

        customer_id = payload.get("customer_id")
        lines = payload.get("lines") or []
        notes = payload.get("notes") or ""

        if not customer_id or not lines:
            return self._json_response(
                {"error": "customer_id y al menos una línea son obligatorios."},
                status=400,
            )

        Partner = request.env["res.partner"].sudo().with_context(lang=user.lang)
        Product = request.env["product.product"].sudo().with_context(lang=user.lang)
        SaleOrder = request.env["sale.order"].sudo().with_context(lang=user.lang)

        partner = Partner.search(
            [("id", "=", customer_id), ("distributor_customer", "=", True)],
            limit=1,
        )
        if not partner:
            return self._json_response(
                {"error": "Cliente no válido para el distribuidor."},
                status=400,
            )

        company = partner.company_id or request.env.company
        pricelist = partner.property_product_pricelist

        order_lines = []
        for line in lines:
            product_id = line.get("product_id")
            qty = float(line.get("quantity") or 0.0)
            if not product_id or qty <= 0:
                continue

            product = Product.search(
                [
                    ("id", "=", product_id),
                    ("sale_ok", "=", True),
                    ("distributor_available", "=", True),
                ],
                limit=1,
            )
            if not product:
                continue

            price = 0.0
            if pricelist:
                price = pricelist._get_product_price(product, qty, partner)

            order_lines.append(
                (
                    0,
                    0,
                    {
                        "product_id": product.id,
                        "product_uom_qty": qty,
                        "price_unit": price,
                    },
                )
            )

        if not order_lines:
            return self._json_response(
                {"error": "No se pudieron generar líneas válidas."},
                status=400,
            )

        order_vals = {
            "partner_id": partner.id,
            "company_id": company.id,
            "pricelist_id": pricelist.id if pricelist else False,
            "note": notes,
            "origin": "App distribuidor",
            # si ya tenés este campo en sale.order, lo marcamos
            "is_distributor_delivery": True,
            "order_line": order_lines,
        }

        order = SaleOrder.create(order_vals)

        return self._json_response(
            {
                "success": True,
                "order_id": order.id,
                "order_name": order.name,
                "state": order.state,
                "amount_total": order.amount_total,
            }
        )

    @http.route(
        "/distributor/api/quotations",
        type="http",
        auth="public",
        methods=["GET"],
        csrf=False,
    )
    def list_quotations(self, **kwargs):
        """
        Lista las últimas cotizaciones creadas para los clientes del distribuidor.

        Query params opcionales:
        - customer_id: filtra por un cliente concreto
        """
        user = request.env.user
        Partner = request.env["res.partner"].sudo().with_context(lang=user.lang)
        SaleOrder = request.env["sale.order"].sudo().with_context(lang=user.lang)

        customer_id = kwargs.get("customer_id")
        distributor_partners = Partner.search([("distributor_customer", "=", True)])

        domain = [
            ("partner_id", "in", distributor_partners.ids),
        ]
        if customer_id:
            try:
                customer_id = int(customer_id)
                domain.append(("partner_id", "=", customer_id))
            except ValueError:
                pass

        orders = SaleOrder.search(domain, order="id desc", limit=50)

        state_labels = {
            "draft": "Presupuesto borrador",
            "sent": "Presupuesto enviado",
            "sale": "Confirmado",
            "cancel": "Cancelado",
        }

        data = []
        for so in orders:
            data.append(
                {
                    "id": so.id,
                    "name": so.name,
                    "date_order": so.date_order,
                    "state": so.state,
                    "state_label": state_labels.get(so.state, so.state),
                    "amount_total": so.amount_total,
                    "partner_name": so.partner_id.display_name,
                }
            )

        return self._json_response({"quotations": data})
