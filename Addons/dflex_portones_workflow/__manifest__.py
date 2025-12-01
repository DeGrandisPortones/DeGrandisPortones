{
    'name': 'DFLEX Portones Workflow',
    'version': '1.0',
    'summary': 'Workflow y estados para portones DFLEX',
    'depends': ['base'],
    'data': [
        'security/dflex_portones_security.xml',
        'security/ir.model.access.csv',
        'views/dflex_porton_workflow_views.xml',
    ],
    'installable': True,
    'application': False,
}