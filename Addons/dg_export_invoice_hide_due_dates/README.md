# DG Factura E sin fechas de vencimiento

Modulo para Odoo 18 que oculta en el PDF de comprobantes E/exportacion:

- Fecha de vencimiento comercial del comprobante.
- Fecha de vencimiento ubicada en el bloque fiscal/CAE cuando aparece renderizada en el PDF.

Se aplica solo a comprobantes AFIP de exportacion E:

- 19 - Factura de exportacion E
- 20 - Nota de debito de exportacion E
- 21 - Nota de credito de exportacion E

No modifica los datos contables ni fiscales del comprobante; solamente limpia el HTML generado para el PDF.

## Instalacion

Copiar la carpeta `dg_export_invoice_hide_due_dates` dentro de `Addons/`, actualizar lista de aplicaciones e instalar el modulo **DG Factura E sin fechas de vencimiento**.


Version 18.0.1.0.1: corrige compatibilidad con la firma de _render_qweb_html en Odoo 18.
