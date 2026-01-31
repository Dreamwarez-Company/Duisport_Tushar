from odoo import models, api, fields
from datetime import date

class ReportWipValuation(models.AbstractModel):
    _name = 'report.dw_customer_credit.report_wip_valuation_template'
    _description = 'WIP Valuation Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        print("=" * 80)
        print("WIP REPORT: _get_report_values called")
        print(f"docids: {docids}")
        
        # Ensure docids is a list
        if not isinstance(docids, (list, tuple)):
            docids = [docids]
        
        # Get the wizard instance
        wizards = self.env['wip.valuation.wizard'].browse(docids)
        wizard = wizards[0] if wizards else None
        
        # Get report data from wizard
        report_data = {}
        if wizard:
            report_data = wizard.get_report_data()
        
        return {
            'doc_ids': docids,
            'doc_model': 'wip.valuation.wizard',
            'docs': wizards,
            'lines': report_data.get('lines', []),
            'total_wip_value': report_data.get('total_wip_value', 0),
            'start_date': report_data.get('start_date', ''),
            'end_date': report_data.get('end_date', ''),
            'current_date': date.today().strftime('%Y-%m-%d'),
            'company': wizard.env.company if wizard else self.env.company,
        }