# Resumen Cta Cte

Modulo para Odoo 18 que permite ver e imprimir la cuenta corriente de un cliente, separada en Subtotal FCA y Subtotal Internas.

## Dependencias

- account
- dg_client_sales_report

## Uso

Contabilidad > Reportes > Resumen Cta Cte

1. Elegir empresa, cliente y rango de fechas.
2. Presionar **Ver detalle**.
3. Odoo muestra el detalle de la cuenta corriente separado por:
   - Subtotal FCA
   - Subtotal Internas
   - Total general
4. Desde el listado, presionar **Descargar resumen** para imprimir el PDF.

El PDF se imprime con el titulo **Reporte de cuenta corriente**.

Los pagos conciliados se asignan al grupo de la factura o saldo inicial contra el que fueron aplicados. Si un pago cancela movimientos de ambos grupos, el reporte lo reparte entre FCA e Internas segun el importe conciliado con cada grupo.
