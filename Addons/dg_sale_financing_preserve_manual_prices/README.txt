DG Fix Ventas - conservar precio y descuento manual
===================================================

Problema:
En ventas, al usar una lista de precios como Mercadolibre y editar manualmente
el precio unitario o el descuento, al guardar la orden el módulo de financiación
recalculaba nuevamente las líneas y pisaba esos valores.

Causa:
El módulo dflex_sale_financing_taca_taca ejecuta _recompute_financing_prices()
en sale.order.write() cuando detecta cambios en order_line. Ese recálculo llama
a _apply_financing_rate(), que vuelve a tomar el precio desde la lista y pone
discount = 0.0.

Corrección:
Este módulo hereda sale.order y sale.order.line para:
- evitar el recálculo de financiación cuando se guardan líneas con precio o
  descuento manual;
- evitar que el onchange de producto/cantidad recalcule precios si no hay
  financiación/cuotas seleccionadas.

Instalación:
1. Copiar la carpeta dg_sale_financing_preserve_manual_prices dentro de Addons.
2. Reiniciar Odoo.
3. Actualizar lista de aplicaciones.
4. Instalar "DG Fix Ventas - conservar precio y descuento manual".

Prueba sugerida:
1. Crear o editar un presupuesto.
2. Seleccionar cliente.
3. Seleccionar lista de precios Mercadolibre.
4. Agregar producto.
5. Editar manualmente precio unitario y/o descuento.
6. Guardar.
7. Verificar que el precio y descuento manual se mantengan.
