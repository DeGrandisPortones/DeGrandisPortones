# Ventas - Localidad en Analisis

## Que hace
Este modulo agrega el campo **Localidad** al modelo `sale.report` para que puedas:

- agrupar el analisis de ventas por localidad
- filtrar por localidad
- ver la localidad en la vista de lista del reporte

La localidad se toma desde `res.partner.city` del cliente del pedido.

## Instalacion
1. Copia la carpeta `sale_report_localidad` dentro de tu ruta de addons custom.
2. Actualiza la lista de aplicaciones.
3. Instala el modulo **Ventas - Localidad en Analisis**.

## Uso
Ir a:
**Ventas -> Reportes -> Ventas**

Luego en el buscador vas a tener:
- el campo **Localidad** para filtrar
- la opcion **Agrupar por -> Localidad**
