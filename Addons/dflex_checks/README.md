```markdown
# Cheques Propios (DFLEX)


Módulo para Odoo que permite:
- Crear chequeras por banco y tipo (Físico / eCheq) con rango [número inicial, cantidad].
- Generar automáticamente los cheques del rango.
- Gestionar estados del cheque: Disponible → Entregado → Debitado (y Anulado).
- Guardar datos: **N° Cheque, Fecha Emisión, Fecha Pago, Importe, Banco, CUIT Proveedor, Razón Social Proveedor, Estado**.


## Instalación
1. Copiar la carpeta `dflex_checks` al `addons_path` del servidor Odoo.
2. Actualizar la lista de apps y activar "Cheques Propios (DFLEX)".


## Uso
1. Contabilidad → **Cheques Propios → Chequeras** → Crear: Banco, Tipo, Nº inicial, Cantidad → **Generar cheques**.
2. Contabilidad → **Cheques Propios → Cheques** para emitir, entregar y debitar.
3. En el formulario del cheque usar los botones **Entregar** y **Debitar** para avanzar el estado.


## Notas
- Multi-compañía soportado.
- Unicidad: mismo **número + banco + compañía**.
- El CUIT/Nombre del proveedor se toma del partner (campos `vat` y `name`).
- Si hace falta vincular con pagos contables, se puede ampliar con hooks en `account.payment`