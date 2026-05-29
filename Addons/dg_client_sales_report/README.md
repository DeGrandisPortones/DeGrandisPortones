# Reporte de Clientes por Diario

Módulo para Odoo 18 que agrega el menú **Contabilidad > Reportes > Reporte de clientes**.

El reporte toma comprobantes publicados de cliente (`out_invoice` y `out_refund`) de diarios de venta y los agrupa por cliente y por:

- **Subtotal FCA**: movimientos del diario **Diario Ventas Preimpreso**.
- **Subtotal Internas**: movimientos del diario **Diario Ventas Internas**.

Al estar agrupado primero por cliente y luego por subtotal, Odoo muestra:

- subtotal por grupo dentro de cada cliente;
- total del cliente, sumando FCA + Internas;
- total general del reporte.

## Instalación

Copiar la carpeta `dg_client_sales_report` dentro de la carpeta `Addons` del repositorio, actualizar la lista de aplicaciones e instalar **Reporte de Clientes por Diario**.

## Notas

El filtro de diarios se hace por nombre exacto:

- `Diario Ventas Preimpreso`
- `Diario Ventas Internas`

Si en la base los diarios tienen otro nombre, cambiar esos textos en `models/dg_client_sales_report.py`.
