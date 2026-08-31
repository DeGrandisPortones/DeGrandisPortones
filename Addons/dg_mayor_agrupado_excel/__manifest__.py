{
    "name": "Mayor Agrupado por Factura (Excel)",
    "version": "18.0.1.0.0",
    "category": "Accounting/Reporting",
    "summary": "Exporta a Excel el mayor de las cuentas elegidas, agrupando cada asiento en una sola fila, sin arrastre de saldos anteriores",
    "description": """
Asistente independiente (no modifica el Libro Mayor estandar ni Mayor Sin Arrastre).

El usuario elige una o mas cuentas contables y un rango de fechas, y el
asistente genera un Excel con, para cada cuenta, una fila por asiento
(factura/nota de credito/etc.) en vez de una fila por linea de factura.
El saldo mostrado es solo del periodo elegido (sin arrastre de saldos
anteriores), calculado con una consulta propia via ORM estandar.
    """,
    "author": "Dflex",
    "license": "LGPL-3",
    "depends": [
        "account",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/mayor_agrupado_wizard_views.xml",
        "views/menu.xml",
    ],
    "installable": True,
    "application": False,
}
