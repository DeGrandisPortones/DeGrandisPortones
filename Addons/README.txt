Modulo: dg_l10n_ar_tax_withholding_counterpart_fix

Instalacion:
1. Copiar la carpeta dg_l10n_ar_tax_withholding_counterpart_fix dentro de Addons.
2. Reiniciar Odoo.
3. Actualizar lista de aplicaciones.
4. Instalar "DG Fix Retenciones Pago Contrapartida".

Que corrige:
- En pagos con retenciones, evita que Odoo balancee la retencion contra Banco.
- La diferencia de retencion se aplica sobre destination_account_id, es decir, la cuenta real de contraparte del pago.
- En tu caso: Deudores por ventas queda acreditado por el total cancelado.

Resultado esperado:
Banco Santander: Debe por el importe neto ingresado.
Retencion ganancias sufrida: Debe por la retencion.
Deudores por ventas: Haber por el total del pago, incluyendo la retencion.

Importante:
- Aplica a pagos nuevos o pagos que vuelvas a borrador y publiques nuevamente.
- Los asientos ya registrados no se corrigen solos.
