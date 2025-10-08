from odoo import fields, models

class DflexPortonSpec(models.Model):
    _name = 'dflex.porton.spec'
    _description = 'Especificación de portón (K/V)'
    _order = 'porton_id, id'

    porton_id = fields.Many2one('dflex.porton', string='Portón', ondelete='cascade', index=True)
    key = fields.Char('Clave', index=True)
    value = fields.Char('Valor', index=True)