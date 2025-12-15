# stock_distirbutor_delivery_api/controllers/distributor_api.py
from odoo import http
from odoo.http import request
import json


class DistributorApi(http.Controller):
    """REST API para distribuidores.

    Endpoints:
      - GET  /distributor/api/pickings
      - POST /distributor/api/pickings/<id>/final_customer
      - GET  /distributor/api/products
      - POST /distributor/api/quotations
    """

    # =====================
    # Helpers
    # =====================

    def _cors_headers(self):
        return [
            ("Access-Control-Allow-Origin", "*"),
            ("Access-Control-Allow-Methods", "GET,POST,OPTIONS"),
            ("Access-Control-Allow-Headers", "Origin,Content-Type,Accept,Authorization"),
        ]

    def _json_response(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False)
        headers = [("Content-Type", "application/json; charset=utf-8")] + self._cors_headers()
        return request.make_response(body, headers=headers, status=status)

    # =====================
    # Pickings (entregas vía distribuidor)
    # =====================

    @http.route(
        "/distributor/api/pickings",
        type="http",
        auth="public",
        methods=["GET", "OPTIONS"],
        csrf=False,
    )
    def distributor_pickings(self, **kwargs):
        """Listado de remitos marcados como 'Entrega vía distribuidor'."""
        # Preflight CORS
        if request.httprequest.method == "OPTIONS":
            return self._json_response({})

        env = request.env
        StockPicking = env["stock.picking"].sudo()

        domain = [
            ("picking_type_id.code", "=", "outgoing"),
            ("is_distributor_delivery", "=", True),
            ("state", "in", ["waiting", "confirmed", "assigned"]),  # pendientes
        ]

        pickings = StockPicking.search(domain, order="scheduled_date, id", limit=200)

        data = []
        for picking in pickings:
            lines = []
            for move in picking.move_ids_without_package:
                lines.append(
                    {
                        "id": move.id,
                        "product_id": move.product_id.id,
                        "product_name": move.product_id.display_name,
                        "quantity": move.product_uom_qty,
                        "uom": move.product_uom.name,
                    }
                )

            data.append(
                {
                    "id": picking.id,
                    "name": picking.name,
                    "origin": picking.origin,
                    "partner_id": picking.partner_id.id,
                    "partner_name": picking.partner_id.display_name,
                    "scheduled_date": picking.scheduled_date.isoformat()
                    if picking.scheduled_date
                    else False,
                    "state": picking.state,
                    "final_customer_completed": picking.final_customer_completed,
                    "final_customer_name": picking.final_customer_name,
                    "final_customer_street": picking.final_customer_street,
                    "final_customer_city": picking.final_customer_city,
                    "final_customer_vat": picking.final_customer_vat,
                    "final_customer_phone": picking.final_customer_phone,
                    "final_customer_email": picking.final_customer_email,
                    "final_customer_notes": picking.final_customer_notes,
                    "lines": lines,
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
    def distributor_set_final_customer(self, picking_id, **kwargs):
        """Guardar datos del cliente final en el picking."""
        if request.httprequest.method == "OPTIONS":
            return self._json_response({})

        try:
            payload = json.loads(request.httprequest.data or "{}")
        except json.JSONDecodeError:
            return self._json_response({"error": "Invalid JSON body"}, status=400)

        env = request.env
        picking = env["stock.picking"].sudo().browse(picking_id)
        if not picking.exists():
            return self._json_response({"error": "Picking not found"}, status=404)

        mapping = {
            "name": "final_customer_name",
            "street": "final_customer_street",
            "city": "final_customer_city",
            "vat": "final_customer_vat",
            "phone": "final_customer_phone",
            "email": "final_customer_email",
            "notes": "final_customer_notes",
        }

        vals = {}
        for key, field_name in mapping.items():
            if key in payload:
                vals[field_name] = payload[key]

        if vals:
            vals["final_customer_completed"] = True
            picking.write(vals)

        return self._json_response(
            {
                "data": {
                    "id": picking.id,
                    "final_customer_completed": picking.final_customer_completed,
                }
            }
        )

    # =====================
    # Productos para presupuestar
    # =====================

    @http.route(
        "/distributor/api/products",
        type="http",
        auth="public",
        methods=["GET", "OPTIONS"],
        csrf=False,
    )
    def distributor_products(self, **kwargs):
        """Lista de productos vendibles para el presupuestador.

        Parámetro opcional:
          - tag_id: filtra por etiqueta de producto (product.tag.id)
        """
        if request.httprequest.method == "OPTIONS":
            return self._json_response({})

        Product = request.env["product.product"].sudo()

        domain = [("sale_ok", "=", True), ("active", "=", True)]

        tag_id = kwargs.get("tag_id")
        if tag_id:
            try:
                tag_id_int = int(tag_id)
                # En Odoo 18 las etiquetas están en product.template
                domain.append(("product_tmpl_id.product_tag_ids", "in", [tag_id_int]))
            except ValueError:
                # si viene basura en tag_id simplemente lo ignoramos
                pass

        products = Product.search(domain, order="default_code, name", limit=300)

        data = []
        for product in products:
            data.append(
                {
                    "id": product.id,
                    "name": product.display_name,
                    "default_code": product.default_code,
                    "uom": product.uom_id.name,
                    "price": product.lst_price,
                }
            )

        return self._json_response({"data": data})

    # =====================
    # Creación de cotizaciones / pedidos
    # =====================

    @http.route(
        "/distributor/api/quotations",
        type="http",
        auth="public",
        methods=["POST", "OPTIONS"],
        csrf=False,
    )
    def distributor_create_quotation(self, **kwargs):
        """Crea una cotización (sale.order) a partir de líneas de productos.

        Espera un JSON como:
        {
          "partner_id": 123,                    # empresa (cliente) sobre la que se genera el pedido
          "client_reference": "Ref del dist.",  # opcional
          "note": "texto libre",                # opcional
          "lines": [
            {"product_id": 10, "quantity": 2},
            {"product_id": 20, "quantity": 1}
          ]
        }
        """
        if request.httprequest.method == "OPTIONS":
            return self._json_response({})

        try:
            payload = json.loads(request.httprequest.data or "{}")
        except json.JSONDecodeError:
            return self._json_response({"error": "Invalid JSON body"}, status=400)

        partner_id = payload.get("partner_id")
        lines_payload = payload.get("lines") or []
        client_reference = payload.get("client_reference") or ""
        note = payload.get("note") or ""

        if not partner_id:
            return self._json_response({"error": "partner_id is required"}, status=400)
        if not lines_payload:
            return self._json_response({"error": "lines is required"}, status=400)

        env = request.env
        Partner = env["res.partner"].sudo()
        partner = Partner.browse(int(partner_id))
        if not partner.exists():
            return self._json_response({"error": "Partner not found"}, status=404)

        Product = env["product.product"].sudo()
        SaleOrder = env["sale.order"].sudo()

        order_lines = []
        for line in lines_payload:
            product_id = line.get("product_id")
            quantity = line.get("quantity") or 0.0
            if not product_id or quantity <= 0:
                continue
            product = Product.browse(int(product_id))
            if not product.exists():
                continue

            order_lines.append(
                (
                    0,
                    0,
                    {
                        "product_id": product.id,
                        "product_uom_qty": quantity,
                    },
                )
            )

        if not order_lines:
            return self._json_response(
                {"error": "No valid order lines received"}, status=400
            )

        order_vals = {
            "partner_id": partner.id,
            "client_order_ref": client_reference,
            "note": note,
            "order_line": order_lines,
        }

        order = SaleOrder.create(order_vals)

        data = {
            "id": order.id,
            "name": order.name,
            "partner_id": order.partner_id.id,
            "partner_name": order.partner_id.display_name,
            "state": order.state,
            "amount_total": order.amount_total,
        }
        return self._json_response({"data": data}, status=201)
