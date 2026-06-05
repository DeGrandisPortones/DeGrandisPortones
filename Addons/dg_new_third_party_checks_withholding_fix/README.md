# DG New Third Party Checks Withholding Fix

Este modulo corrige el flujo de retenciones cuando se cobra con el metodo de pago:

- `new_third_party_checks` / Nuevo cheque de Terceros Existente

El modulo `l10n_ar_tax` ya trae tratamiento especial para pagos con cheques, pero solo contempla:

- `in_third_party_checks`
- `out_third_party_checks`

Al no contemplar `new_third_party_checks`, el recibo podia confirmarse sin ajustar correctamente el importe total cancelado por la retencion.

## Resultado esperado

Para un cobro con cheque de terceros y retencion, el asiento debe quedar asi:

Debe:
- Cheques de terceros en cartera por el neto del cheque
- Retenciones sufridas por el importe de la retencion

Haber:
- Deudores por ventas por el total cancelado

## Instalacion

Copiar la carpeta `dg_new_third_party_checks_withholding_fix` dentro de `Addons`, actualizar lista de aplicaciones e instalar el modulo.

## Uso

Si al confirmar un cobro con cheque de terceros existente aparece un aviso diciendo que las retenciones cambian el importe a pagar, volver al pago, computar el importe/retenciones y confirmar nuevamente.
