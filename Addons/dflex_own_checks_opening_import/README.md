# DFlex - Importar cheques propios en circulacion

Modulo para cargar cheques propios historicos/en circulacion usando el modelo existente `dflex.check`.

Por cada fila del CSV crea:

1. Un cheque propio `dflex.check` en estado Entregado / Por ingresar / Vencido.
2. Un asiento de alta:
   - Debe: Capital integrado.
   - Haber: Cheques propios.

Luego el boton existente "Debitar cheque" del modulo `dflex_checks` hace:

- Debe: Cheques propios.
- Haber: Banco del diario del cheque.

## Uso seguro

1. Instalar el modulo.
2. Ir a Contabilidad > Cheques Propios > Importar cheques en circulacion.
3. Cargar el CSV.
4. Elegir compania DFLEX ARGENTINA S.A.S.
5. Elegir diario Banco Santander.
6. Elegir diario de alta, cuenta Capital integrado y cuenta puente Cheques propios.
7. Ejecutar primero con "Solo simular, no crear nada" activo.
8. Revisar el resumen.
9. Repetir con simulacion desactivada. Dejar "Publicar asientos de alta" desactivado para que queden en borrador.

## Columnas CSV

Obligatorias:

- `number`: numero del cheque.
- `amount`: importe.

Opcionales:

- `payment_date`: fecha de pago/vencimiento, formato `YYYY-MM-DD` o `DD/MM/YYYY`.
- `issue_date`: fecha de emision.
- `delivery_date`: fecha de entrega.
- `partner_vat`: CUIT del proveedor/beneficiario.
- `partner_name`: nombre del proveedor/beneficiario.
- `type`: `fisico` o `echeq`.
- `state`: `delivered`, `pending_entry` o `expired`. Tambien acepta equivalentes en espanol.
- `note`: observaciones.
