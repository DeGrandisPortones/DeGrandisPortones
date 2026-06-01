# Resumen Cta Cte

Modulo Odoo 18 para consultar e imprimir el resumen de cuenta corriente de un cliente, separado en FCA e Internas.

## Flujo

1. Contabilidad > Reportes > Resumen Cta Cte.
2. Elegir empresa, cliente y rango de fechas.
3. Ver detalle.
4. Odoo muestra solo tres filas principales: Subtotal FCA, Subtotal Internas y Total.
5. Desde Subtotal FCA se abre el detalle de ventas, notas y cobranzas FCA.
6. Desde Subtotal Internas se abre el detalle de ventas, notas y cobranzas internas.
7. Desde Total se abre el detalle combinado.
8. Los botones de PDF existen solo en esas filas: Descargar FCA, Descargar Internas y Descargar ambas.

## Movimientos incluidos

- Facturas de cliente.
- Notas de credito de cliente.
- Notas de debito de cliente.
- Recibos / cobranzas.
- Saldo anterior solo si esta activada la opcion y existe saldo previo al rango.

## Version

18.0.1.5.0
