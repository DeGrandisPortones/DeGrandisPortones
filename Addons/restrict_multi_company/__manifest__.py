{
    'name': 'Restrict Multi Company Selection',
    'version': '18.0.1.1.0',
    'summary': 'Impide que los usuarios (salvo id=2) tengan más de una empresa activa a la vez, también al recargar o al abrir registros de otra empresa.',
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
