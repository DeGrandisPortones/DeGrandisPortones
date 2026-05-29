# Resumen Cta Cte

Modulo para Odoo 18 que permite generar un listado de cuenta corriente por cliente y descargar un PDF separado en Subtotal FCA y Subtotal Internas.

## Dependencias

- account
- dg_client_sales_report

## Uso

Contabilidad > Reportes > Resumen Cta Cte

1. Elegir empresa, rango de fechas y clientes opcionales.
2. Presionar **Ver listado**.
3. Desde el listado, seleccionar uno o varios clientes o usar el boton de la fila.
4. Presionar **Descargar resumen** para imprimir el PDF.

El PDF se imprime con el titulo **Reporte de cuenta corriente** y separa los movimientos en:

- Subtotal FCA
- Subtotal Internas
- Total general

Los pagos conciliados se asignan al grupo de la factura o saldo inicial contra el que fueron aplicados. Si un pago cancela movimientos de ambos grupos, el reporte lo reparte entre FCA e Internas segun el importe conciliado con cada grupo.
