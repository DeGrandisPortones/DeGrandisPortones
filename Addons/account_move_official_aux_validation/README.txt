Reemplazo del módulo: account_move_official_aux_validation

Qué hace:
- SOLO muestra una advertencia (no bloqueante) cuando un ASIENTO MANUAL mezcla cuentas 1-5 con 6-9.
- NO bloquea el posteo.

Dónde avisa:
1) Mientras editás (onchange en líneas): popup warning.
2) Al postear: notificación sticky (display_notification) para asegurar visibilidad.

Instalación:
- Copiar/reemplazar carpeta Addons/account_move_official_aux_validation en el repo.
- Actualizar Apps (modo dev) y hacer Upgrade del módulo.
