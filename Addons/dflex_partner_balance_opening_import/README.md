# DFlex - Importar saldos iniciales de contactos

Wizard para importar saldos iniciales de clientes separados por FCA e INTERNO.

## Asiento generado

Si el saldo es positivo:

Debe: Cuenta clientes FCA o Cuenta clientes Interno
Haber: Capital integrado

Si el saldo es negativo:

Debe: Capital integrado
Haber: Cuenta clientes FCA o Cuenta clientes Interno

## Menú

Contabilidad > Clientes > Importar saldos iniciales de contactos

## CSV

Columnas mínimas: `grupo;razsoc;cuit;saldo`.

El CSV incluido es `templates/DG_saldos_contactos_fca_interno.csv`.


## Version 18.0.1.1.0

Esta version crea un unico asiento de apertura con:
- una linea por contacto/saldo contra la cuenta de clientes FCA o Interno;
- una o dos lineas de contrapartida contra Capital integrado, segun haya saldos positivos y/o negativos.
