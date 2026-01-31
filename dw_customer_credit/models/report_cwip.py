from odoo import api, models
import json

class ReportCWIP(models.AbstractModel):
    _name = 'report.dw_customer_credit.report_cwip_report_template'
    _description = 'CWIP Report'
    
    @api.model
    def _get_report_values(self, docids, data=None):
        # Get the wizard records
        wizards = self.env['cwip.report.wizard'].browse(docids)
        wizard = wizards[0] if wizards else None
        
        # Get data from wizard
        lines = []
        if wizard and wizard.cwip_data_json:
            try:
                lines = json.loads(wizard.cwip_data_json)
            except:
                lines = []
        
        # Calculate totals
        total_cwip_value = sum(line.get('cwip_value', 0) for line in lines)
        
        # Count statuses
        status_count = {
            'Not Started': 0,
            'In Progress': 0,
            'Depreciation Started': 0,
            'Completed': 0
        }
        
        for line in lines:
            status = line.get('cwip_status', 'Unknown')
            if status in status_count:
                status_count[status] += 1
        
        return {
            'doc_ids': docids,
            'doc_model': 'cwip.report.wizard',
            'docs': wizards,
            'lines': lines,
            'date_as_of': wizard.date_as_of if wizard else None,
            'category_id': wizard.category_id if wizard else None,
            'partner_id': wizard.partner_id if wizard else None,
            'status': wizard.status if wizard else None,
            'project_ref': wizard.project_ref if wizard else None,
            'location': wizard.location if wizard else None,
            'total_cwip_value': total_cwip_value,
            'total_assets': len(lines),
            'status_count': status_count,
        }