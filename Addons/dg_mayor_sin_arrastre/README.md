# Mayor sin Arrastre

Modulo para Odoo 18 que afecta solamente el reporte estandar:

Contabilidad / Reportes / Libro mayor

Objetivo: que el Libro mayor se vea sin arrastre de saldos anteriores al periodo filtrado.
Si se filtra un mes, las cuentas deben quedar afectadas solamente por los asientos de ese mes.

## Importante

Este modulo NO depende de `dg_resumen_cta_cte` y NO toca el Resumen Cta Cte.

## Instalacion

1. Copiar la carpeta `mayor_sin_arrastre` dentro de la carpeta de addons.
2. Reiniciar Odoo.
3. Actualizar lista de aplicaciones.
4. Instalar o actualizar el modulo `Mayor sin Arrastre`.

Por consola:

```bash
./odoo-bin -d TU_BASE -u mayor_sin_arrastre --stop-after-init
```

## Dependencia

Requiere `account_reports`, porque modifica el handler del Libro mayor estandar de Odoo.
