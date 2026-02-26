Reemplaza el módulo account_move_official_aux_validation por esta versión.
Esta versión hace SOLO:
- Advertencia en asientos MANUALES si mezcla cuentas 1-5 con 6-9.
  * Popup (onchange) mientras se edita.
  * Toast (notify_warning) al postear, por si el onchange no se disparó.
- NO bloquea el posteo.
