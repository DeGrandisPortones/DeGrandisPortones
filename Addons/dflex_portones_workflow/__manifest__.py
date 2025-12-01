{
    'name': 'DFLEX Portones - Workflow Estados',
    'version': '16.0.1.0.0',
    'author': 'Esteban + ChatGPT',
    'category': 'Sales',
    'summary': 'Workflow de estados para portones DFLEX',
    'depends': ['base'],
    'data': [
        'security/ir.model.access.csv',
        'views/dflex_porton_workflow_views.xml'
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}