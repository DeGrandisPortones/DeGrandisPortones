{
    'name': 'Restrict Multi Company Selection',
    'version': '18.0.1.2.0',
    'summary': 'Impide que cualquier usuario tenga más de una empresa activa a la vez, también al recargar o al abrir registros de otra empresa.',
    'depends': ['web'],
    'assets': {
        'web.assets_backend': [
            'restrict_multi_company/static/src/js/switch_company_patch.js',
        ],
    },
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
