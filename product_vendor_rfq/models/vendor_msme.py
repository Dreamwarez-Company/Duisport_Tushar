from odoo import models, fields, api
import base64
import io
import xlsxwriter

class ResPartnerMsme(models.Model):
    _inherit = 'res.partner'

    # is_msme = fields.Boolean("MSME Vendor")
    # udyam_number = fields.Char("Udyam Registration Number")
    is_msme_user = fields.Boolean("MSME Vendor")
    udyam_number_user = fields.Char("Udyam Registration Number")

    def action_download_msme_list(self):
        """Generate and download MSME vendor list as Excel"""

        # Get MSME vendors
        vendors = self.env['res.partner'].search([('is_msme', '=', True)])

        # Create Excel in memory
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output)
        sheet = workbook.add_worksheet("MSME Vendors")

        # Header
        headers = ["Vendor Name", "Udyam Number", "GSTIN", "PAN", "Phone", "Email"]
        for col, head in enumerate(headers):
            sheet.write(0, col, head)

        # Data
        row = 1
        for v in vendors:
            sheet.write(row, 0, v.name or '')
            sheet.write(row, 1, v.udyam_number or '')
            sheet.write(row, 2, v.vat or '')
            sheet.write(row, 3, v.l10n_in_pan or '')
            sheet.write(row, 4, v.phone or '')
            sheet.write(row, 5, v.email or '')
            row += 1

        workbook.close()
        output.seek(0)
        file_data = output.read()
        output.close()

        # Return as attachment download
        return {
            'type': 'ir.actions.act_url',
            'url': f"/web/content/?model=res.partner&download=true&field=datas&filename=msme_vendors.xlsx&filename_field=name&data={base64.b64encode(file_data).decode()}",
            'target': 'self',
        }