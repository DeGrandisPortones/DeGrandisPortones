# DG Account Lock Exception by User

Módulo para Odoo 18 que agrega un asistente para crear excepciones de bloqueo contable para un usuario específico.

## Uso

1. Instalar el módulo.
2. Ir a **Contabilidad > Configuración > Desbloqueos por usuario**.
3. Elegir el usuario, el tipo de bloqueo a flexibilizar y la nueva fecha de bloqueo para ese usuario.
4. Crear la excepción.

## Ejemplo

Si la compañía tiene bloqueado hasta `30/04/2026` y se quiere permitir que un usuario cargue o modifique asientos de abril, seleccionar ese usuario y usar `31/03/2026` como nueva fecha de bloqueo.

## Notas

- No habilita a todos los usuarios.
- No aplica al bloqueo permanente (`hard_lock_date`), porque Odoo no permite excepciones para ese bloqueo.
- Requiere permisos de Administrador de Contabilidad.
