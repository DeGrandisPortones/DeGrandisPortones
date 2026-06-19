{
    'name': 'Restrict Multi Company Selection',
    'version': '18.0.1.0.0',
    'summary': 'Impide que usuarios no administradores tengan más de una empresa activa simultáneamente.',
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
