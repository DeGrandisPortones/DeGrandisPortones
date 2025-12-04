# stock_distributor_delivery_api/controllers/distributor_api.py
import json

from odoo import http
from odoo.http import request


class DistributorApiController(http.Controller):
    """
    API simple para la app del distribuidor (o para testear con curl/Postman):

    - GET  /distributor/api/pickings
        Lista las entregas marcadas como 'Entrega vía distribuidor':
        * Solo salidas (picking_type_id.code = 'outgoing')
        * Solo estados pendientes (confirmed / assigned)
        * Incluye tanto las que tienen cliente final cargado como las que no
        * Incluye detalle de líneas (productos y cantidades)

    - POST /distributor/api/pickings/<picking_id>/final_customer
        Guarda los datos del cliente final para esa entrega.
    """

    def _json_response(self, data, status=200):
        body = json.dumps(data, default=str)
        headers = [
            ("Content-Type", "application/json"),
            ("Access-Control-Allow-Origin", "*"),  # abierto para pruebas
            ("Access-Control-Allow-Methods", "GET, POST, OPTIONS"),
            ("Access-Control-Allow-Headers", "Content-Type, Authorization"),
        ]
        response = request.make_response(body, headers)
        response.status_code = status
        return response

    @http.route(
        "/distributor/api/pickings",
        type="http",
        auth="public",   # para pruebas; luego se puede pasar a 'userasda'
        methods=["GET", "OPTIONS"],
        csrf=False,
    )
    def list_pickings(self, **kwargs):
        """
        Devuelve las entregas pendientes para distribuidor.

        Dominio:
        - picking_type_id.code = 'outgoing'
        - state in ['confirmed', 'assigned']
        - is_distributor_delivery = True

        Nota: NO filtramos por final_customer_completed para que,
        una vez cargado el cliente final, sigan apareciendo hasta
        que el despachante marque la entrega como hecha (state = 'done').
        """
        if request.httprequest.method == "OPTIONS":
            return self._json_response({}, status=200)

        user = request.env.user

        Picking = request.env["stock.picking"].sudo().with_context(lang=user.lang)

        domain = [
            ("picking_type_id.code", "=", "outgoing"),
            ("state", "in", ["confirmed", "assigned"]),
            ("is_distributor_delivery", "=", True),
        ]

        pickings = Picking.search(domain, order="scheduled_date, id")

        data = []
        for picking in pickings:
            # Detalle de líneas de productos
            lines = []
            for move in picking.move_ids_without_package:
                lines.append(
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
                    "lines": lines,
                }
            )

        return self._json_response({"data": data})

    @http.route(
        "/distributor/api/pickings/<int:picking_id>/final_customer",
        type="http",
        auth="public",   # para pruebas; luego se puede pasar a 'user'
        methods=["POST", "OPTIONS"],
        csrf=False,
    )
    def set_final_customer(self, picking_id, **kwargs):
        """
        Guarda los datos del cliente final para un picking concreto.

        Body esperado (JSON):
        {
            "name": "...",
            "street": "...",
            "city": "...",
            "vat": "...",
            "phone": "...",
            "notes": "..."
        }
        """
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
