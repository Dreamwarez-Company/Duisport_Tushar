from odoo import api, models
from datetime import date

class ReportAssetDisposal(models.AbstractModel):
    _name = 'report.dw_customer_credit.report_asset_disposal_template'
    _description = 'Asset Disposal Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        # data will contain 'start_date', 'end_date', etc. passed from the wizard
        start_date = data.get('start_date') if data else None
        end_date = data.get('end_date') if data else None
        journal_id = data.get('journal_id') if data else None
        asset_category_id = data.get('asset_category_id') if data else None

        # Get the wizard instance to call its methods
        wizard = self.env['asset.disposal.wizard'].browse(docids)
        
        # Get disposal lines using wizard method
        lines = wizard._get_disposal_lines()
        total_amount = wizard._get_total_disposal_amount()

        return {
            'doc_ids': docids,
            'doc_model': 'asset.disposal.wizard',
            'data': data or {},
            'docs': self.env['asset.disposal.wizard'].browse(docids),
            'lines': lines,
            'total_amount': total_amount,
            'start_date': start_date,
            'end_date': end_date,
            'current_date': date.today().strftime('%Y-%m-%d'),  # Add current date
        }