# Reporte de Clientes por Diario

Módulo para Odoo 18 que agrega el menú **Contabilidad > Reportes > Reporte de clientes**.

El reporte toma comprobantes publicados de cliente (`out_invoice` y `out_refund`) de diarios de venta y los agrupa por cliente y por:

- **Subtotal FCA**: movimientos del diario **Diario Ventas Preimpreso**.
- **Subtotal Internas**: movimientos del diario **Diario Ventas Internas**.

Al estar agrupado primero por cliente y luego por subtotal, Odoo muestra:

- subtotal por grupo dentro de cada cliente;
- total del cliente, sumando FCA + Internas;
- total general del reporte.

## Saldos iniciales / ajustes de clientes

Para importar clientes que ya vienen con saldo, no conviene cargarlos como facturas si esos importes ya fueron contabilizados en el sistema anterior, porque podrían afectar ventas e impuestos.

El módulo también toma apuntes contables publicados de tipo cuenta por cobrar (`asset_receivable`) desde asientos contables (`entry`) cuando se cumpla una de estas condiciones:

1. El apunte contable tiene el campo **Grupo reporte clientes** con valor:
   - `Subtotal FCA`
   - `Subtotal Internas`
2. O el asiento está en uno de estos diarios:
   - **Saldos Iniciales FCA**
   - **Saldos Iniciales Internas**

Para importar saldos discriminados por cliente:

- crear o usar un asiento de apertura;
- cargar una línea por cliente y por tipo de saldo;
- usar la cuenta contable de clientes / cuentas por cobrar;
- indicar el cliente en `partner_id`;
- si se usa un único diario de apertura, importar la columna **Grupo reporte clientes** en cada línea;
- si se prefieren diarios separados, usar **Saldos Iniciales FCA** para FCA y **Saldos Iniciales Internas** para internas.

Ejemplo conceptual:

| Cliente | Cuenta | Debe | Haber | Grupo reporte clientes |
|---|---:|---:|---:|---|
| Cliente A | Clientes | 100000 | 0 | Subtotal FCA |
| Cliente A | Clientes | 50000 | 0 | Subtotal Internas |
| Cuenta de apertura | Saldos iniciales | 0 | 150000 | |

En el reporte, las líneas de saldos iniciales aparecen con **Origen del saldo = Saldo inicial / ajuste**.

## Instalación

Copiar la carpeta `dg_client_sales_report` dentro de la carpeta `Addons` del repositorio, actualizar la lista de aplicaciones e instalar **Reporte de Clientes por Diario**.

## Notas

El filtro de diarios de comprobantes se hace por nombre exacto:

- `Diario Ventas Preimpreso`
- `Diario Ventas Internas`

El filtro de diarios de saldos iniciales también se hace por nombre exacto:

- `Saldos Iniciales FCA`
- `Saldos Iniciales Internas`

Si en la base los diarios tienen otro nombre, cambiar esos textos en `models/dg_client_sales_report.py`.


## Corrección 18.0.1.1.2

Se ajustó la lectura del nombre del diario para Odoo 18. En esta versión algunos campos traducibles, como `account.journal.name`, se almacenan como JSONB en PostgreSQL. El reporte ahora extrae el nombre traducido antes de compararlo con `Diario Ventas Preimpreso`, `Diario Ventas Internas`, `Saldos Iniciales FCA` o `Saldos Iniciales Internas`.


## 18.0.1.1.2

- Reempaquetado con nombre versionado para evitar descargas cacheadas.
- Correccion confirmada de comparacion de diarios traducibles JSON en Odoo 18.
