## __manifest__.py

{
"name": "Cheques Propios (DFLEX)",
"summary": "Gestión de chequeras y cheques propios (físicos y eCheq)",
"version": "16.0.1.0.0", # compatible con 16-18, actualiza si hace falta
"author": "DFLEX Argentina SAS",
"website": "https://dflex.com.ar",
"category": "Accounting/Payments",
"license": "LGPL-3",
"depends": ["account", "base"],
"data": [
"security/ir.model.access.csv",
"views/check_views.xml",
],
"application": False,
"installable": True,
}
