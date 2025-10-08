from odoo import fields, models

class DflexPortonSpec(models.Model):
    _name = 'dflex.porton.spec'
    _description = 'Especificación de portón (K/V)'
    _order = 'porton_id, id'

    porton_id = fields.Many2one('dflex.porton', ondelete='cascade', index=True, string='Portón')
    key = fields.Char(index=True, string='Clave')
    value = fields.Char(index=True, string='Valor')