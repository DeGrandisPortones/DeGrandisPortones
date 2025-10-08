{
    'name': 'DFLEX Portones - Importador',
    'version': '18.0.1.0.0',
    'summary': 'Importa portones desde Excel/XLS para tabular especificaciones.',
    'author': 'Esteban Scalerandi + ChatGPT',
    'website': 'https://dflex.com.ar',
    'category': 'Manufacturing/Manufacturing',
    'license': 'LGPL-3',
    'depends': ['base'],
    'data': [
        'security/ir.model.access.csv',
        'views/porton_menu.xml',
        'views/porton_views.xml',
        'views/porton_spec_views.xml',
        'wizard/import_wizard_views.xml',
    ],
    'assets': {},  # No web assets yet
    'installable': True,
    'application': False,
}