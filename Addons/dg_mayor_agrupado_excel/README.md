# Mayor Agrupado por Factura (Excel)

Módulo para Odoo 18 que agrega un asistente independiente (no toca el Libro
Mayor estándar ni el módulo `dg_mayor_sin_arrastre`).

## Qué hace

1. El usuario elige una o más cuentas contables y un rango de fechas.
2. El asistente arma un Excel con, para cada cuenta, una sección con **una
   fila por asiento** (factura, nota de crédito, etc.) en vez de una fila
   por línea de factura — sumando débito/crédito de todas las líneas de esa
   cuenta que pertenecen al mismo asiento.
3. El saldo mostrado es solo del período elegido, sin arrastre de saldos
   anteriores (equivalente en concepto a "Mayor Sin Arrastre", pero
   agrupado por asiento).

## Por qué es un módulo aparte

El Libro Mayor estándar de Odoo (`account_reports`, Enterprise) genera sus
líneas con un motor de reportes dinámico cuyo código fuente no está
disponible localmente para verificar con seguridad cómo agrupar sin romper
la paginación ("cargar más") del reporte real.

Para evitar ese riesgo, este asistente no depende de `account_reports` en
absoluto: arma la consulta con el ORM estándar de Odoo
(`account.move.line.read_group`) y exporta directo a Excel con
`xlsxwriter`. Así "Mayor Sin Arrastre" y el Libro Mayor estándar quedan
completamente intactos.

## Instalación / actualización

1. Copiar la carpeta `dg_mayor_agrupado_excel` dentro de la carpeta de
   addons.
2. Reiniciar Odoo.
3. Actualizar la lista de aplicaciones.
4. Instalar el módulo `Mayor Agrupado por Factura (Excel)`.

Por consola:

```bash
./odoo-bin -d TU_BASE -u dg_mayor_agrupado_excel --stop-after-init
```

## Dependencia

Solo requiere `account` (el módulo base de Contabilidad de Odoo).
