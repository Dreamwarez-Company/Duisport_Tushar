from odoo import fields,  models, api




class AccountTDSSection(models.Model):
    _name = "account.tds.section"
    _description = "TDS Section"

    name = fields.Char(string="Section Name")  # e.g., 194C, 194J
    rate = fields.Float(string="TDS Rate (%)")
    description = fields.Text(string="Description")








class AccountMove(models.Model):
    _inherit = "account.move"

    def _apply_vendor_specific_tax(self):
        """Apply vendor specific tax on vendor bills."""
        for rec in self:
            partner = rec.partner_id
            if rec.move_type in ('in_invoice', 'in_refund') and partner.vendor_specific_tax_id:
                vendor_tax = partner.vendor_specific_tax_id
                for line in rec.invoice_line_ids:
                    if vendor_tax not in line.tax_ids:
                        line.tax_ids = [(4, vendor_tax.id)]

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records._apply_vendor_specific_tax()
        return records

    def write(self, vals):
        res = super().write(vals)
        self._apply_vendor_specific_tax()
        return res
