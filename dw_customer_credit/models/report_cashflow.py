from odoo import api, models
import json

class ReportCashflow(models.AbstractModel):
    _name = 'report.dw_customer_credit.report_cashflow_template'
    _description = 'Cash Flow Forecast Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        # Get the wizard records
        wizards = self.env['dw.cashflow.forecast.wizard'].browse(docids)
        
        # We'll work with the first wizard
        wizard = wizards[0] if wizards else None
        
        # Get lines from wizard's JSON data
        lines = []
        if wizard and wizard.cashflow_lines_json:
            try:
                lines = json.loads(wizard.cashflow_lines_json)
            except:
                lines = []
        
        # Calculate totals
        total_inflow = sum(line.get('inflow', 0) for line in lines)
        total_outflow = sum(line.get('outflow', 0) for line in lines)
        net_cash_flow = total_inflow - total_outflow
        
        return {
            'doc_ids': docids,
            'doc_model': 'dw.cashflow.forecast.wizard',
            'docs': wizards,
            'lines': lines,  # Pass lines directly to template
            'start_date': wizard.start_date if wizard else None,
            'end_date': wizard.end_date if wizard else None,
            'total_inflow': total_inflow,
            'total_outflow': total_outflow,
            'net_cash_flow': net_cash_flow,
        }