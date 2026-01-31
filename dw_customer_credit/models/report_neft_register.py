from odoo import api, models
import json

class ReportNeftRegister(models.AbstractModel):
    _name = 'report.dw_customer_credit.report_neft_register_template'
    _description = 'NEFT Register Report'
    
    @api.model
    def _get_report_values(self, docids, data=None):
        # Get the wizard records
        wizards = self.env['neft.register.wizard'].browse(docids)
        wizard = wizards[0] if wizards else None
        
        # Get data from wizard
        lines = []
        if wizard and wizard.neft_data_json:
            try:
                lines = json.loads(wizard.neft_data_json)
            except:
                lines = []
        
        # Calculate totals
        total_amount = sum(line.get('amount', 0) for line in lines)
        
        # Count transaction types
        vendor_count = sum(1 for line in lines if line.get('payment_type') == 'outbound')
        transfer_count = sum(1 for line in lines if line.get('payment_type') == 'transfer')
        customer_count = sum(1 for line in lines if line.get('payment_type') == 'inbound')
        
        return {
            'doc_ids': docids,
            'doc_model': 'neft.register.wizard',
            'docs': wizards,
            'lines': lines,
            'date_from': wizard.date_from if wizard else None,
            'date_to': wizard.date_to if wizard else None,
            'journal_id': wizard.journal_id if wizard else None,
            'total_amount': total_amount,
            'vendor_count': vendor_count,
            'transfer_count': transfer_count,
            'customer_count': customer_count,
        }