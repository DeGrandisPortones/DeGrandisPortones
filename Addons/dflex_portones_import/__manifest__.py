{
    'name': 'DFLEX Portones - Importador',
    'version': '18.0.1.0.5',
    'summary': 'Importa portones desde Excel/XLS (hoja PRINCIPAL) y tabula especificaciones.',
    'author': 'Esteban Scalerandi + ChatGPT',
    'website': 'https://dflex.com.ar',
    'category': 'Manufacturing/Manufacturing',
    'license': 'LGPL-3',
    'depends': ['base'],
    'data': [
        'security/ir.model.access.csv',
        'views/porton_views.xml',
        'views/porton_spec_views.xml',
        'views/import_wizard_views.xml',
        'views/porton_menu.xml'
    ],
    'assets': {},
    'installable': True,
    'application': False,
}