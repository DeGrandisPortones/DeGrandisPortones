from odoo import models, fields

class DflexPorton(models.Model):
    _name = "dflex.porton"
    _description = "Portones (bootstrap)"
    name = fields.Char("Identificador (NV)", required=True, index=True)
