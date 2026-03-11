Instalar el modulo l10n_ar_perception_zero_default.

Comportamiento:
- Si en el widget de tax totals se agrega un grupo de percepcion nuevo y Odoo lo inicializa en 1,
  el modulo lo fuerza a 0.
- Solo afecta grupos de percepcion definidos en la posicion fiscal argentina.
- No toca otros impuestos ni grupos ya existentes.
