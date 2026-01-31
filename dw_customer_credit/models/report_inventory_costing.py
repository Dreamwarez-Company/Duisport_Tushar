from odoo import api, models
from datetime import date

class ReportInventoryCosting(models.AbstractModel):
    _name = 'report.dw_customer_credit.report_inventory_costing_template'
    _description = 'Inventory & Costing Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        print("=" * 80)
        print("INVENTORY REPORT: _get_report_values called")
        print(f"docids: {docids}")
        
        # Ensure docids is a list
        if not isinstance(docids, (list, tuple)):
            docids = [docids]
        
        # Get the wizard instance
        wizards = self.env['inventory.costing.wizard'].browse(docids)
        wizard = wizards[0] if wizards else None
        
        # Get report data from wizard
        report_data = {}
        if wizard:
            report_data = wizard.get_report_data()
        
        return {
            'doc_ids': docids,
            'doc_model': 'inventory.costing.wizard',
            'docs': wizards,
            'report_data': report_data,
            'start_date': wizard.start_date.strftime('%Y-%m-%d') if wizard and wizard.start_date else '',
            'end_date': wizard.end_date.strftime('%Y-%m-%d') if wizard and wizard.end_date else '',
            'report_type': wizard.report_type if wizard else 'summary',
            'current_date': date.today().strftime('%Y-%m-%d'),
            'company': wizard.env.company if wizard else self.env.company,
        }