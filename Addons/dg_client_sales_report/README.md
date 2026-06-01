# Reporte de Clientes por Diario

Modulo para Odoo 18 que agrega el menu **Contabilidad > Reportes > Reporte de clientes**.

El objetivo es ver la deuda de clientes de forma similar a cuentas por cobrar vencidas, pero separada por origen:

- **Subtotal FCA**: ventas oficiales / preimpresas.
- **Subtotal Internas**: ventas internas / no oficiales.

El reporte muestra solamente movimientos con saldo pendiente. Si una factura fue pagada totalmente, no aparece. Si fue pagada parcialmente, aparece por el saldo pendiente.

## Diarios de venta

El reporte clasifica automaticamente estos nombres de diario:

- `Ventas Preimpreso` o `Diario Ventas Preimpreso` -> **Subtotal FCA**.
- `Ventas Internas` o `Diario Ventas Internas` -> **Subtotal Internas**.

Ademas, el modulo agrega el campo **Grupo reporte clientes** en los diarios contables para que no dependas del nombre del diario. Recomendado:

- En el diario **Ventas Preimpreso**, completar **Grupo reporte clientes = Subtotal FCA**.
- En el diario **Ventas Internas**, completar **Grupo reporte clientes = Subtotal Internas**.

## Pagos

Los pagos aplicados a facturas no se muestran como linea separada: reducen el saldo de la factura.

Ejemplo: si una factura de **Ventas Internas** por 100.000 recibe un pago de 40.000, el reporte muestra esa factura dentro de **Subtotal Internas** con saldo 60.000.

Si un pago queda sin imputar o como anticipo, puede aparecer como credito pendiente. En ese caso se puede clasificar manualmente usando **Grupo reporte clientes** en el apunte contable, o el reporte intentara inferir el grupo si el pago ya estuvo conciliado parcialmente contra facturas de un unico grupo.

## Saldos iniciales / ajustes de clientes

Para importar clientes que ya vienen con saldo, no conviene cargarlos como facturas si esos importes ya fueron contabilizados en el sistema anterior, porque podrian afectar ventas e impuestos.

El modulo toma apuntes contables publicados de tipo cuenta por cobrar (`asset_receivable`) desde asientos contables (`entry`) cuando tengan saldo pendiente y se puedan clasificar por alguno de estos caminos:

1. El apunte contable tiene el campo **Grupo reporte clientes** con valor:
   - `Subtotal FCA`
   - `Subtotal Internas`
2. El diario del asiento tiene **Grupo reporte clientes** configurado.
3. El diario se llama:
   - `Saldos Iniciales FCA`
   - `Saldos Iniciales Internas`

Para importar saldos discriminados por cliente:

- crear o usar un asiento de apertura;
- cargar una linea por cliente y por tipo de saldo;
- usar la cuenta contable de clientes / cuentas por cobrar;
- indicar el cliente en `partner_id`;
- importar la columna **Grupo reporte clientes** en cada linea, o usar diarios ya clasificados.

Ejemplo conceptual:

| Cliente | Cuenta | Debe | Haber | Grupo reporte clientes |
|---|---:|---:|---:|---|
| Cliente A | Clientes | 100000 | 0 | Subtotal FCA |
| Cliente A | Clientes | 50000 | 0 | Subtotal Internas |
| Cuenta de apertura | Saldos iniciales | 0 | 150000 | |

En el reporte, esas lineas aparecen con **Origen del saldo = Saldo inicial / ajuste**.

## Multiempresa

El reporte respeta companias permitidas. Si tenes seleccionadas dos empresas a la vez, podes ver deuda de ambas; si seleccionas solo una empresa, ves solo esa.

## Instalacion

Copiar la carpeta `dg_client_sales_report` dentro de la carpeta `Addons`, actualizar la lista de aplicaciones e instalar o actualizar **Reporte de Clientes por Diario**.

## 18.0.1.2.0

- Se agrego soporte para los nombres reales `Ventas Preimpreso` y `Ventas Internas`.
- Se agrego campo de clasificacion en diarios: **Grupo reporte clientes**.
- El reporte ahora usa saldos pendientes, no totales historicos pagados.
- Los pagos aplicados reducen el saldo de la factura del grupo correspondiente.
- Se agrego soporte para pagos/creditos sin aplicar cuando se puedan clasificar o inferir.
- Se agrego regla multiempresa.


## 18.0.1.2.1

- Se agrego el campo **Grupo reporte clientes** en las lineas de **Asientos contables > Apuntes contables**.
- El campo queda disponible como columna para cargar saldos iniciales FCA o Internas directamente desde el asiento de apertura.
