{
    'name': 'DFLEX Portones - Workflow portones',
    'version': '16.0.1.0.0',
    'summary': 'Estados y aprobaciones del portón (Acopio / Medición / Pre-producción / Producción)',
    'author': 'Esteban + ChatGPT',
    'category': 'Sales/CRM',
    'license': 'LGPL-3',
    'depends': [
        'base',
    ],
    'data': [
        'security/dflex_portones_security.xml',
        'views/dflex_porton_workflow_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
