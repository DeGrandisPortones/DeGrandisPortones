{
    'name': 'DFLEX Portones - Importador',
    'version': '18.0.1.0.1',
    'summary': 'Importa portones desde Excel/XLS para tabular especificaciones.',
    'author': 'Esteban Scalerandi + ChatGPT',
    'website': 'https://dflex.com.ar',
    'category': 'Manufacturing/Manufacturing',
    'license': 'LGPL-3',
    'depends': ['base'],
    'data': [
        'security/ir.model.access.csv',
        'views/porton_views.xml',          # define action first
        'views/porton_spec_views.xml',     # define related views
        'views/porton_menu.xml',           # then reference actions in menus
        'wizard/import_wizard_views.xml',
    ],
    'assets': {},
    'installable': True,
    'application': False,
}