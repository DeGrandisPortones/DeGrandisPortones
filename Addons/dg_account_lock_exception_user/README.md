# DG Account Lock Exception by User

Módulo para Odoo 18 que agrega un historial de excepciones de bloqueo contable y permite crear desbloqueos para un usuario específico.

## Ubicación del menú

**Contabilidad > Contabilidad > Desbloqueos contables**

El menú abre primero el listado/historial de excepciones. Desde ahí se puede:

- ver excepciones activas, revocadas o expiradas;
- seleccionar registros y usar **Revocar**;
- entrar al formulario del registro y usar **Revocar** desde el encabezado;
- crear una nueva excepción con **Nuevo desbloqueo por usuario**.

## Uso

1. Instalar o actualizar el módulo.
2. Ir a **Contabilidad > Contabilidad > Desbloqueos contables**.
3. Click en **Nuevo desbloqueo por usuario**.
4. Elegir el usuario, el tipo de bloqueo a flexibilizar y la nueva fecha de bloqueo para ese usuario.
5. Crear la excepción. Al confirmar, vuelve al historial.

## Ejemplo

Si la compañía tiene bloqueado hasta `30/04/2026` y se quiere permitir que un usuario cargue o modifique asientos de abril, seleccionar ese usuario y usar `31/03/2026` como nueva fecha de bloqueo.

## Notas

- No habilita a todos los usuarios.
- No aplica al bloqueo permanente (`hard_lock_date`), porque Odoo no permite excepciones para ese bloqueo.
- Requiere permisos de Administrador de Contabilidad.
