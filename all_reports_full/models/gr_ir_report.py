# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError
import io, base64
from datetime import date

try:
    import xlsxwriter
except Exception:
    xlsxwriter = None

class GRIRReport(models.TransientModel):
    _name = 'gr.ir.report'
    _description = 'GR/IR Report'

    start_date = fields.Date(string='Start Date', required=True)
    end_date = fields.Date(string='End Date', required=True)
    line_ids = fields.One2many('gr.ir.line', 'report_id', string='Lines')

    def action_view_report(self):
        """Fetch and display report data"""
        self.line_ids.unlink()
        
        pos = self.env['purchase.order'].search([
            ('date_order', '>=', self.start_date),
            ('date_order', '<=', self.end_date),
            ('state', 'in', ['purchase', 'done'])
        ])
        
        lines_to_create = []   
        for po in pos:
            for line in po.order_line:
                ordered = float(line.product_qty or 0.0)
                received = float(line.qty_received or 0.0)
                invoiced = float(line.qty_invoiced or 0.0)
                diff = received - invoiced
                
                # Only show lines with differences
                if diff != 0:
                    lines_to_create.append({
                        'report_id': self.id,
                        'po_number': po.name,
                        'vendor': po.partner_id.name or '',
                        'product_name': line.product_id.name or '',
                        'ordered_qty': ordered,
                        'received_qty': received,
                        'invoiced_qty': invoiced,
                        'difference': diff,
                    })
        
        self.env['gr.ir.line'].create(lines_to_create)
        
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'gr.ir.report',
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'new',
        }

    def action_download_pdf(self):
            """Download PDF report"""
            return self.env.ref('all_reports_full.report_gr_ir_pdf').report_action(self)


    def get_report_data(self):
        """Get data for PDF report"""
        pos = self.env['purchase.order'].search([
            ('date_order', '>=', self.start_date),
            ('date_order', '<=', self.end_date),
            ('state', 'in', ['purchase', 'done'])
        ])
        return pos


class GRIRLine(models.TransientModel):
    _name = 'gr.ir.line'
    _description = 'GR/IR Line'

    report_id = fields.Many2one('gr.ir.report', string='Report', ondelete='cascade')
    po_number = fields.Char(string='PO')
    vendor = fields.Char(string='Vendor')
    product_name = fields.Char(string='Product')
    ordered_qty = fields.Float(string='Ordered Qty')
    received_qty = fields.Float(string='Received Qty')
    invoiced_qty = fields.Float(string='Invoiced Qty')
    difference = fields.Float(string='Difference (GR-IR)')