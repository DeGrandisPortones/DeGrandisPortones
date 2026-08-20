# Mayor sin Arrastre

Modulo para Odoo 18 que agrega un reporte de Libro Mayor sin arrastre de saldos anteriores al periodo filtrado.

## Exportacion XLSX

Desde la version 18.0.2.24.0, la exportacion XLSX respeta el estado de expansion visible en pantalla:

- Si ninguna cuenta esta desplegada, exporta solamente el resumen por cuenta.
- Si se desplegaron cuentas manualmente, exporta el detalle solamente de esas cuentas.
- Si se activo "Desplegar todo", exporta todas las cuentas desplegadas.

## Instalacion / actualizacion

1. Copiar la carpeta `dg_mayor_sin_arrastre` dentro de la carpeta de addons.
2. Reiniciar Odoo.
3. Actualizar la lista de aplicaciones.
4. Actualizar el modulo `Mayor sin Arrastre`.

Por consola:

```bash
./odoo-bin -d TU_BASE -u dg_mayor_sin_arrastre --stop-after-init
```

## Dependencia

Requiere `account_reports`, porque modifica el handler del Libro Mayor estandar de Odoo.

## Correccion 18.0.2.24.0

El centinela usado para evitar el auto-desplegado de Odoo ahora usa el formato interno valido de IDs de lineas (`markup~model~id`). Esto evita el `ValueError` al parsear `unfolded_lines` durante la exportacion XLSX.
