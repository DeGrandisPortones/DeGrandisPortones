{
    'name': 'DFlex - Importador de Portones (Excel)',
    'version': '1.0',
    'category': 'Manufacturing',
    'summary': 'Importa portones desde un archivo Excel y genera fichas automáticas',
    'depends': ['base', 'mrp'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/x_gate_spec_views.xml',
        'views/x_gate_import_batch_views.xml',
        'views/gate_import_wizard_views.xml',
        'views/menuitems.xml',
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
