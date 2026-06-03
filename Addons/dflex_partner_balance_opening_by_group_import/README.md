# DFlex - Importar saldos clientes por grupo reporte

Crea un asiento unico por importacion para FCA o Interno.

Cada linea de cliente usa la misma cuenta saldo cliente elegida en el wizard y carga
`dg_client_sales_report_group` con `Subtotal FCA` o `Subtotal Internas`.

La contrapartida acumulada usa la cuenta Capital integrado elegida antes de importar.

## Uso

1. Instalar o actualizar el modulo.
2. Ir a `Contabilidad > Clientes > Importar saldos clientes por grupo`.
3. Ejecutar primero con `Solo simular`.
4. Hacer una importacion para FCA con `DG_saldos_contactos_FCA.csv`.
5. Hacer otra importacion para Interno con `DG_saldos_contactos_INTERNO.csv`.


## Version 18.0.2.1.0

La cuenta de ajuste / Capital integrado se carga una sola vez por asiento, por la diferencia neta entre el Debe y el Haber de las lineas de clientes.
