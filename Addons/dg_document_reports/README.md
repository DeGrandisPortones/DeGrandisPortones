# DG Document Reports

Primera version del reporte alternativo **Factura DG**.

- No reemplaza ni modifica el reporte nativo de Odoo.
- Agrega una opcion adicional en **Imprimir > Factura DG**.
- Usa un formato inspirado en la factura historica de Androvetto.
- El NV se toma del ID interno del pedido de venta relacionado.
- Para FA-A 00006-00001174 debe imprimir: `NV 4470`.
- Incluye detalle, neto, impuestos, total, CAE y QR.

Instalacion:
1. Descomprimir `dg_document_reports` dentro de la carpeta de addons custom.
2. Reiniciar/reconstruir Odoo.
3. Actualizar lista de aplicaciones.
4. Instalar `DG Document Reports`.
5. Abrir una factura y usar `Imprimir > Factura DG`.
