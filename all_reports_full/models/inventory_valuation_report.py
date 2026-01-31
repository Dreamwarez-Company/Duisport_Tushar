# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError
import io, base64
from datetime import date

try:
    import xlsxwriter
except Exception:
    xlsxwriter = None

class InventoryValuationReport(models.TransientModel):
    _name = 'inventory.valuation.report'
    _description = 'Inventory Valuation Report'

    date_from = fields.Date(string='From Date', required=True)
    date_to = fields.Date(string='To Date', required=True)
    product_id = fields.Many2one('product.product', string='Product')
    categ_id = fields.Many2one('product.category', string='Product Category')
    line_ids = fields.One2many('inventory.valuation.line', 'report_id', string='Lines')
    total_value = fields.Float(string='Total Inventory Value', compute='_compute_total_value')

    @api.depends('line_ids.total_value')
    def _compute_total_value(self):
        for rec in self:
            rec.total_value = sum(rec.line_ids.mapped('total_value'))

    def action_view_report(self):
        """Fetch and display report data"""
        self.line_ids.unlink()
        
        # Build domain for products
        domain = [('type', '=', 'product')]
        if self.product_id:
            domain.append(('id', '=', self.product_id.id))
        if self.categ_id:
            domain.append(('categ_id', 'child_of', self.categ_id.id))
        
        products = self.env['product.product'].search(domain)
        lines_to_create = []
        
        for p in products:
            # Get stock moves within date range
            moves_in = self.env['stock.move'].search([
                ('product_id', '=', p.id),
                ('date', '>=', self.date_from),
                ('date', '<=', self.date_to),
                ('state', '=', 'done'),
                ('location_dest_id.usage', '=', 'internal'),
            ])
            
            moves_out = self.env['stock.move'].search([
                ('product_id', '=', p.id),
                ('date', '>=', self.date_from),
                ('date', '<=', self.date_to),
                ('state', '=', 'done'),
                ('location_id.usage', '=', 'internal'),
            ])
            
            qty_in = sum(moves_in.mapped('product_uom_qty'))
            qty_out = sum(moves_out.mapped('product_uom_qty'))
            net_qty = qty_in - qty_out
            
            # Current quantity on hand
            quants = self.env['stock.quant'].search([
                ('product_id', '=', p.id),
                ('location_id.usage', '=', 'internal')
            ])
            current_qty = sum(quants.mapped('quantity'))
            
            if current_qty == 0 and net_qty == 0:
                continue
            
            unit_cost = float(p.standard_price or 0.0)
            value = unit_cost * float(current_qty)
            
            lines_to_create.append({
                'report_id': self.id,
                'product_name': p.name,
                'sku': p.default_code or '',
                'category': p.categ_id.name if p.categ_id else '',
                'qty_in': qty_in,
                'qty_out': qty_out,
                'qty_on_hand': current_qty,
                'unit_cost': unit_cost,
                'total_value': value,
            })
        
        self.env['inventory.valuation.line'].create(lines_to_create)
        
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'inventory.valuation.report',
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'new',
        }

    def action_download_xlsx(self):
        """Download Excel report"""
        if xlsxwriter is None:
            raise UserError(_('Python library xlsxwriter is required for Excel export.'))
        
        workbook_stream = io.BytesIO()
        workbook = xlsxwriter.Workbook(workbook_stream, {'in_memory': True})
        sheet = workbook.add_worksheet('Inventory Valuation')
        
        # Headers
        headers = ['Product', 'SKU', 'Category', 'Qty In', 'Qty Out', 'Qty On Hand', 'Unit Cost', 'Total Value']
        for col, h in enumerate(headers):
            sheet.write(0, col, h)
        
        # Build domain for products
        domain = [('type', '=', 'product')]
        if self.product_id:
            domain.append(('id', '=', self.product_id.id))
        if self.categ_id:
            domain.append(('categ_id', 'child_of', self.categ_id.id))
        
        products = self.env['product.product'].search(domain)
        row = 1
        total_value = 0
        
        for p in products:
            # Get stock moves within date range
            moves_in = self.env['stock.move'].search([
                ('product_id', '=', p.id),
                ('date', '>=', self.date_from),
                ('date', '<=', self.date_to),
                ('state', '=', 'done'),
                ('location_dest_id.usage', '=', 'internal'),
            ])
            
            moves_out = self.env['stock.move'].search([
                ('product_id', '=', p.id),
                ('date', '>=', self.date_from),
                ('date', '<=', self.date_to),
                ('state', '=', 'done'),
                ('location_id.usage', '=', 'internal'),
            ])
            
            qty_in = sum(moves_in.mapped('product_uom_qty'))
            qty_out = sum(moves_out.mapped('product_uom_qty'))
            
            # Current quantity on hand
            quants = self.env['stock.quant'].search([
                ('product_id', '=', p.id),
                ('location_id.usage', '=', 'internal')
            ])
            current_qty = sum(quants.mapped('quantity'))
            
            if current_qty == 0 and qty_in == 0 and qty_out == 0:
                continue
            
            unit_cost = float(p.standard_price or 0.0)
            value = unit_cost * float(current_qty)
            total_value += value
            
            sheet.write(row, 0, p.name)
            sheet.write(row, 1, p.default_code or '')
            sheet.write(row, 2, p.categ_id.name if p.categ_id else '')
            sheet.write(row, 3, float(qty_in))
            sheet.write(row, 4, float(qty_out))
            sheet.write(row, 5, float(current_qty))
            sheet.write(row, 6, float(unit_cost))
            sheet.write(row, 7, float(value))
            row += 1
        
        # Total row
        sheet.write(row, 6, 'Total:')
        sheet.write(row, 7, float(total_value))
        
        workbook.close()
        
        attachment = self.env['ir.attachment'].create({
            'name': f'inventory_valuation_{self.date_from}_{self.date_to}.xlsx',
            'type': 'binary',
            'datas': base64.b64encode(workbook_stream.getvalue()),
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        })
        
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'self',
        }

    def action_download_pdf(self):
        """Download PDF report"""
        return self.env.ref('all_reports_full.report_inventory_valuation_pdf').report_action(self)


class InventoryValuationLine(models.TransientModel):
    _name = 'inventory.valuation.line'
    _description = 'Inventory Valuation Line'

    report_id = fields.Many2one('inventory.valuation.report', string='Report', ondelete='cascade')
    product_name = fields.Char(string='Product')
    sku = fields.Char(string='SKU')
    category = fields.Char(string='Category')
    qty_in = fields.Float(string='Qty In')
    qty_out = fields.Float(string='Qty Out')
    qty_on_hand = fields.Float(string='Quantity On Hand')
    unit_cost = fields.Float(string='Unit Cost')
    total_value = fields.Float(string='Total Value')