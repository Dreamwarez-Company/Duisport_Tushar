from odoo import api, models
import json
from datetime import datetime

class ReportAssetDisposal(models.AbstractModel):
    _name = 'report.dw_customer_credit.report_asset_disposal_template'
    _description = 'Asset Disposal Report'
    
    @api.model
    def _get_report_values(self, docids, data=None):
        # Get the wizard records
        wizards = self.env['asset.disposal.wizard'].browse(docids)
        wizard = wizards[0] if wizards else None
        
        # Get data from wizard
        lines = []
        if wizard and wizard.disposal_data_json:
            try:
                lines = json.loads(wizard.disposal_data_json)
            except:
                lines = []
        
        # Calculate totals
        total_disposal_amount = sum(line.get('disposal_amount', 0) for line in lines)
        
        # Count by category
        category_count = {}
        for line in lines:
            category = line.get('asset_category', 'Unknown')
            if category in category_count:
                category_count[category] += 1
            else:
                category_count[category] = 1
        
        # Current date for report
        current_date = datetime.now().strftime('%Y-%m-%d')
        
        return {
            'doc_ids': docids,
            'doc_model': 'asset.disposal.wizard',
            'docs': wizards,
            'lines': lines,
            'start_date': wizard.start_date if wizard else None,
            'end_date': wizard.end_date if wizard else None,
            'journal_id': wizard.journal_id if wizard else None,
            'asset_category_id': wizard.asset_category_id if wizard else None,
            'total_disposal_amount': total_disposal_amount,
            'total_records': len(lines),
            'category_count': category_count,
            'current_date': current_date,
        }