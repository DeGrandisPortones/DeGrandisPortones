# Resumen Cta Cte

Modulo Odoo 18 para consultar e imprimir el resumen de cuenta corriente de un cliente, separado en FCA e Internas.

## Flujo

1. Contabilidad > Reportes > Resumen Cta Cte.
2. Elegir empresa, cliente y rango de fechas.
3. Ver detalle.
4. El listado muestra solo movimientos de cuenta corriente:
   - Facturas de cliente.
   - Notas de credito de cliente.
   - Notas de debito de cliente.
   - Recibos / cobranzas.
5. El listado muestra un unico subtotal por FCA, un unico subtotal por Internas y un unico total.
6. Solo esas tres filas tienen boton de descarga:
   - Descargar FCA.
   - Descargar Internas.
   - Descargar ambas.

## Version

18.0.1.4.0
