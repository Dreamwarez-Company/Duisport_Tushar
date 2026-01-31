
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

#     tds_rate = fields.Float(
#     string="TDS Rate (%)",
#     readonly=True,
#     store=True
# )


    tds_rate = fields.Float(
        string="TDS Rate (%)",
        related='tds_section_id.rate',
        store=True,
        readonly=True
    )


    @api.model
    def create(self, vals):
        if vals.get('tds_section_id'):
            section = self.env['tds.section.master'].browse(vals['tds_section_id'])
            vals['tds_rate'] = section.rate
        return super().create(vals)


    def write(self, vals):
        if vals.get('tds_section_id'):
            section = self.env['tds.section.master'].browse(vals['tds_section_id'])
            vals['tds_rate'] = section.rate
        return super().write(vals)


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
    _rec_name = "code"

    name = fields.Char(required=True)
    code = fields.Char(required=True)
    rate = fields.Float(required=True)
    residency = fields.Selection([
        ('yes', 'Resident'),
        ('no', 'Non-Resident')
    ], required=True)
    short_note = fields.Char(string='Criteria')

    tds_tax_id = fields.Many2one(
        'account.tax',
        string='TDS Tax',
        domain=[('type_tax_use','=','purchase')]
    )


    def name_get(self):
        result = []
        for rec in self:
            result.append((rec.id, rec.code))
        return result



class AccountMove(models.Model):
    _inherit = "account.move"

    def _apply_vendor_tds_tax(self):
        for move in self:
            if move.move_type not in ('in_invoice', 'in_refund'):
                continue

            partner = move.partner_id
            if not partner or not partner.tds_section_id:
                continue

            tds_tax = partner.tds_section_id.tds_tax_id
            if not tds_tax:
                continue

            for line in move.invoice_line_ids:
                # Skip section/note lines
                if line.display_type:
                    continue

                # Apply TDS only once
                if tds_tax not in line.tax_ids:
                    line.tax_ids = [(4, tds_tax.id)]

    @api.model_create_multi
    def create(self, vals_list):
        moves = super().create(vals_list)
        moves._apply_vendor_tds_tax()
        return moves

    def write(self, vals):
        res = super().write(vals)
        self._apply_vendor_tds_tax()
        return res
