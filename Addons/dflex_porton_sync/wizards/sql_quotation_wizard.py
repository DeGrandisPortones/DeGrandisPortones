from odoo import models, fields, api, _
from odoo.exceptions import UserError

try:
    import pyodbc
except ImportError:
    pyodbc = None


class SqlQuotationWizard(models.TransientModel):
    _name = "dflex.sql.quotation.wizard"
    _description = "Crear cotización desde SQL Server"

    customer_id = fields.Many2one(
        "res.partner",
        string="Cliente",
        required=True,
    )
    sql_internal_id = fields.Char(
        string="ID Pedido SQL (NTASVTAS.idpedido)",
        required=True,
        help="Valor del campo NTASVTAS.idpedido en la base Portones.",
    )

    @api.model
    def _get_sql_connection(self):
        if pyodbc is None:
            raise UserError(
                _(
                    "La librería pyodbc no está instalada en el entorno de Odoo. "
                    "Instalala en el servidor para poder conectarte a SQL Server."
                )
            )

        # String de conexión leído desde parámetros del sistema.
        # Crear en Ajustes > Técnico > Parámetros del sistema
        #   Clave: dflex_porton_sync.sql_connection_string
        #   Valor ejemplo:
        #   DRIVER={ODBC Driver 17 for SQL Server};SERVER=SERVIDOR\\INSTANCIA;DATABASE=Portones;UID=usuario;PWD=clave;
        icp = self.env["ir.config_parameter"].sudo()
        conn_str = icp.get_param("dflex_porton_sync.sql_connection_string")
        if not conn_str:
            raise UserError(
                _(
                    "No se encontró el parámetro de sistema "
                    "'dflex_porton_sync.sql_connection_string'.\n"
                    "Configurá allí el string de conexión ODBC a SQL Server."
                )
            )

        try:
            return pyodbc.connect(conn_str)
        except Exception as e:
            raise UserError(_("Error conectando a SQL Server: %s") % e)

    def action_create_quotation(self):
        self.ensure_one()

        conn = self._get_sql_connection()
        cursor = conn.cursor()

        # ========================
        # 1) Leer cabecera NTASVTAS
        # ========================
        header_sql = """
            SELECT
                fecha,
                tipo,
                sucursal,
                numero,
                deposito,
                cliente,
                nombre,
                direccion,
                localidad,
                cp,
                provincia,
                fpago,
                vendedor,
                operador,
                zona,
                iva,
                cuit,
                ibrutos,
                observ,
                retrep,
                fechaent,
                dirent,
                obs,
                oc,
                idpedido,
                condicion,
                remito
            FROM Portones.dbo.NTASVTAS
            WHERE idpedido = ?
        """
        cursor.execute(header_sql, self.sql_internal_id)
        header = cursor.fetchone()
        if not header:
            conn.close()
            raise UserError(
                _("No se encontró ningún registro en NTASVTAS con idpedido = %s")
                % self.sql_internal_id
            )

        (
            fecha,
            tipo,
            sucursal,
            numero,
            deposito,
            cliente_codigo,
            nombre_cliente_sql,
            direccion,
            localidad,
            cp,
            provincia,
            fpago,
            vendedor,
            operador,
            zona,
            iva,
            cuit,
            ibrutos,
            observ,
            retrep,
            fechaent,
            dirent,
            obs2,
            oc,
            idpedido,
            condicion,
            remito,
        ) = header

        # =====================
        # 2) Leer líneas IVENTAS
        # =====================
        lines_sql = """
            SELECT
                producto,
                descripcion,
                cantidad,
                precio,
                bonific,
                preneto,
                prelista
            FROM Portones.dbo.IVENTAS
            WHERE interno = ?
        """
        cursor.execute(lines_sql, self.sql_internal_id)
        line_rows = cursor.fetchall()

        if not line_rows:
            conn.close()
            raise UserError(
                _("No se encontraron líneas en IVENTAS con interno = %s")
                % self.sql_internal_id
            )

        SaleOrder = self.env["sale.order"]
        SaleOrderLine = self.env["sale.order.line"]
        Product = self.env["product.product"]

        # Crear pedido de venta en Odoo
        order_vals = {
            "partner_id": self.customer_id.id,
            "origin": "NTASVTAS %s" % self.sql_internal_id,
        }
        if fecha:
            order_vals["date_order"] = fields.Datetime.to_string(fecha)
        if tipo or sucursal or numero:
            order_vals["client_order_ref"] = "%s-%s-%s" % (
                tipo or "",
                sucursal or "",
                numero or "",
            )

        order = SaleOrder.create(order_vals)

        # Crear líneas
        for row in line_rows:
            (
                producto_codigo,
                descripcion,
                cantidad,
                precio,
                bonific,
                preneto,
                prelista,
            ) = row

            # Elegimos precio neto si existe, si no el precio normal
            price_unit = preneto if preneto not in (None, 0) else precio
            discount = float(bonific or 0.0)

            # Buscamos el producto en Odoo, primero por nombre (descripcion),
            # luego por default_code (codigo)
            domain = ["|", ("name", "=", descripcion), ("default_code", "=", producto_codigo)]
            product = Product.search(domain, limit=1)
            if not product:
                conn.close()
                raise UserError(
                    _(
                        "Producto no encontrado en Odoo para la línea SQL.\n"
                        "Código: %s\nDescripción: %s"
                    )
                    % (producto_codigo, descripcion)
                )

            line_vals = {
                "order_id": order.id,
                "product_id": product.id,
                "name": descripcion,
                "product_uom_qty": float(cantidad or 0.0),
                "price_unit": float(price_unit or 0.0),
                "discount": discount,
            }
            SaleOrderLine.create(line_vals)

        conn.close()

        # Forzamos recálculo de totales y creamos el registro de portón
        order._amount_all()

        Porton = self.env["x_dflex.porton"]
        Porton.create(
            {
                "sale_order_id": order.id,
                "base_value": order.amount_total,
            }
        )

        action = self.env.ref("sale.action_quotations").read()[0]
        action["res_id"] = order.id
        action["views"] = [
            (self.env.ref("sale.view_order_form").id, "form"),
        ]
        return action