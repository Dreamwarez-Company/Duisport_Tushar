
from odoo import models, fields, api

class ResPartner(models.Model):
    _inherit = 'res.partner'

    is_indian_resident = fields.Selection([
        ('yes', 'Resident of India'),
        ('no', 'Non-Resident')
    ], string='Residency Status')

    tds_section_id = fields.Many2one(
        'tds.section.master',
        string='TDS Section'
    )

    tds_rate = fields.Float(string='TDS Rate (%)', readonly=True)

    @api.onchange('is_indian_resident')
    def _onchange_residency(self):
        self.tds_section_id = False
        self.tds_rate = 0.0

    @api.onchange('tds_section_id')
    def _onchange_tds_section(self):
        if self.tds_section_id:
            self.tds_rate = self.tds_section_id.rate
        else:
            self.tds_rate = 0.0


class TdsSectionMaster(models.Model):
    _name = 'tds.section.master'
    _description = 'TDS Section Master'

    name = fields.Char(required=True)
    code = fields.Char(required=True)
    rate = fields.Float(required=True)
    residency = fields.Selection([
        ('yes', 'Resident'),
        ('no', 'Non-Resident')
    ], required=True)
    short_note = fields.Char(string='Criteria')
