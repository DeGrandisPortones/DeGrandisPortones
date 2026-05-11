Parche Cheques de terceros - vista historica + deposito directo

Que corrige
-----------
1) Restaura el menu Cheques de terceros para que muestre todos los cheques de terceros:
   - En cartera
   - Entregado
   - Depositado
   - Vendido

   Antes el parche anterior dejaba el dominio del menu limitado a ux_destination_type = En cartera.
   Ahora la distincion se hace desde los filtros de busqueda, no desde el dominio base de la accion.

2) Mantiene el deposito directo correcto:
   Debe: Banco destino
   Haber: Cheques de Terceros en cartera

Instalacion
-----------
1) Descomprimir este zip sobre la carpeta de addons, reemplazando archivos existentes.
2) Reiniciar/buildar Odoo.
3) Actualizar modulos:

   ./odoo-bin -d TU_BASE -u l10n_latam_check_ux,l10n_latam_check_direct_deposit --stop-after-init

Desde interfaz:
- Modo desarrollador
- Aplicaciones
- Actualizar lista de aplicaciones
- Actualizar l10n_latam_check_ux
- Actualizar l10n_latam_check_direct_deposit

Nota contable
-------------
Los cheques depositados/vendidos correctamente tienen que tener una linea en la cuenta contable
del banco destino. Si una operacion vieja quedo contabilizada contra Ingresos pendientes o no toco
la cuenta del banco, no va a aparecer en el mayor del banco hasta revertirla y rehacerla, o hacer
el asiento correctivo correspondiente.
