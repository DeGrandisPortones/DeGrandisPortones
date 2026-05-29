# Resumen Cta Cte

Modulo para Odoo 18 que imprime un PDF de cuenta corriente por cliente, separado en Subtotal FCA y Subtotal Internas.

## Dependencias

- account
- dg_client_sales_report

## Uso

Contabilidad > Reportes > Resumen Cta Cte

Filtros:

- Empresa
- Clientes
- Fecha desde
- Fecha hasta
- Incluir saldo anterior

El PDF se imprime con el titulo **Reporte de cuenta corriente** y separa los movimientos en:

- Subtotal FCA
- Subtotal Internas
- Total general

Los pagos conciliados se asignan al grupo de la factura o saldo inicial contra el que fueron aplicados. Si un pago cancela movimientos de ambos grupos, el reporte lo reparte entre FCA e Internas segun el importe conciliado con cada grupo.
