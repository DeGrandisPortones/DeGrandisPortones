# DFlex - Importar cheques de terceros en cartera

Importa cheques de terceros de apertura usando el circuito nativo de `l10n_latam_check`.

## Asiento esperado al publicar cada pago

Debe: cuenta de recibos pendientes del método `new_third_party_checks` del diario, normalmente `Cheques de Terceros en cartera`.

Haber: `3.1.1.01.002 Capital integrado`.

## Uso

1. Copiar la carpeta `dflex_third_party_checks_opening_import` dentro de `Addons`.
2. Reiniciar Odoo.
3. Actualizar lista de apps.
4. Instalar `DFlex - Importar cheques de terceros en cartera`.
5. Ir a `Contabilidad > Clientes > Importar cheques de terceros en cartera`.
6. Elegir compañía `DFLEX ARGENTINA S.A.S.`, diario `Cheques de Terceros`, método `new_third_party_checks`, cuenta `3.1.1.01.002 Capital integrado`.
7. Subir el CSV.
8. Simular primero.
9. Ejecutar real. Para que queden plenamente en cartera, publicar los pagos o activar `Publicar pagos de apertura`.

## CSV incluido

`templates/cheques_terceros_en_cartera_capital_integrado.csv`
