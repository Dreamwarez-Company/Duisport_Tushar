# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError
import io, base64
from datetime import date

try:
    import xlsxwriter
except Exception:
    xlsxwriter = None

class StockRegisterReport(models.TransientModel):
    _name = 'stock.register.report'
    _description = 'Stock Register Report'

    start_date = fields.Date(string='From Date', required=True, default=fields.Date.context_today)
    end_date = fields.Date(string='To Date', required=True, default=fields.Date.context_today)
    product_ids = fields.Many2many('product.product', string='Products')
    category_ids = fields.Many2many('product.category', string='Product Categories')
    line_ids = fields.One2many('stock.register.line', 'report_id', string='Lines')
    report_generated = fields.Boolean(string='Report Generated', default=False)

    def _get_domain(self):
        """Build search domain based on filters"""
        domain = [
            ('date', '>=', self.start_date),
            ('date', '<=', self.end_date),
            ('state', '=', 'done')
        ]
        
        # Product filter
        if self.product_ids:
            domain.append(('product_id', 'in', self.product_ids.ids))
        
        # Category filter
        if self.category_ids:
            domain.append(('product_id.categ_id', 'child_of', self.category_ids.ids))
        
        return domain

    def action_generate_report(self):
        """Generate and display report data"""
        self.line_ids.unlink()
        
        domain = self._get_domain()
        moves = self.env['stock.move'].search(domain, order='date, product_id')
        
        if not moves:
            raise UserError(_('No stock moves found for the selected filters.'))
        
        lines_to_create = []
        
        for m in moves:
            lines_to_create.append({
                'report_id': self.id,
                'date': m.date,
                'reference': m.reference or m.picking_id.name or '',
                'product_name': m.product_id.name or '',
                'sku': m.product_id.default_code or '',
                'category': m.product_id.categ_id.name or '',
                'quantity': m.product_uom_qty or 0.0,
                'uom': m.product_uom.name or '',
                'source_location': m.location_id.complete_name or '',
                'dest_location': m.location_dest_id.complete_name or '',
                'status': m.state or '',
            })
        
        self.env['stock.register.line'].create(lines_to_create)
        self.report_generated = True
        
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'stock.register.report',
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'new',
            'context': {'form_view_initial_mode': 'edit'}
        }

    def action_download_xlsx(self):
        """Download Excel report"""
        if not self.report_generated:
            raise UserError(_('Please generate the report first by clicking "Generate Report" button.'))
            
        if xlsxwriter is None:
            raise UserError(_('Python library xlsxwriter is required for Excel export.'))
        
        workbook_stream = io.BytesIO()
        workbook = xlsxwriter.Workbook(workbook_stream, {'in_memory': True})
        sheet = workbook.add_worksheet('Stock Register')
        
        # Define formats
        header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#D3D3D3',
            'border': 1,
            'align': 'center',
            'valign': 'vcenter'
        })
        
        cell_format = workbook.add_format({
            'border': 1,
            'align': 'left',
            'valign': 'vcenter'
        })
        
        number_format = workbook.add_format({
            'border': 1,
            'align': 'right',
            'valign': 'vcenter',
            'num_format': '#,##0.00'
        })
        
        # Set column widths
        sheet.set_column('A:A', 12)  # Date
        sheet.set_column('B:B', 20)  # Reference
        sheet.set_column('C:C', 30)  # Product
        sheet.set_column('D:D', 15)  # SKU
        sheet.set_column('E:E', 20)  # Category
        sheet.set_column('F:F', 12)  # Qty
        sheet.set_column('G:G', 10)  # UOM
        sheet.set_column('H:H', 25)  # Source
        sheet.set_column('I:I', 25)  # Dest
        sheet.set_column('J:J', 12)  # Status
        
        # Headers
        headers = ['Date', 'Reference', 'Product', 'SKU', 'Category', 'Quantity', 'UOM', 
                   'Source Location', 'Destination Location', 'Status']
        for col, h in enumerate(headers):
            sheet.write(0, col, h, header_format)
        
        # Data
        domain = self._get_domain()
        moves = self.env['stock.move'].search(domain, order='date, product_id')
        row = 1
        
        for m in moves:
            sheet.write(row, 0, str(m.date), cell_format)
            sheet.write(row, 1, m.reference or m.picking_id.name or '', cell_format)
            sheet.write(row, 2, m.product_id.name or '', cell_format)
            sheet.write(row, 3, m.product_id.default_code or '', cell_format)
            sheet.write(row, 4, m.product_id.categ_id.name or '', cell_format)
            sheet.write(row, 5, float(m.product_uom_qty or 0.0), number_format)
            sheet.write(row, 6, m.product_uom.name or '', cell_format)
            sheet.write(row, 7, m.location_id.complete_name or '', cell_format)
            sheet.write(row, 8, m.location_dest_id.complete_name or '', cell_format)
            sheet.write(row, 9, m.state or '', cell_format)
            row += 1
        
        workbook.close()
        
        filename = f'stock_register_{self.start_date}_{self.end_date}.xlsx'
        attachment = self.env['ir.attachment'].create({
            'name': filename,
            'type': 'binary',
            'datas': base64.b64encode(workbook_stream.getvalue()),
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'res_model': self._name,
            'res_id': self.id,
        })
        
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'self',
        }

    def action_download_pdf(self):
        """Download PDF report"""
        if not self.report_generated:
            raise UserError(_('Please generate the report first by clicking "Generate Report" button.'))
            
        return self.env.ref('all_reports_full.report_stock_register_pdf').report_action(self)

    def get_report_data(self):
        """Get data for PDF report"""
        domain = self._get_domain()
        return self.env['stock.move'].search(domain, order='date, product_id')


class StockRegisterLine(models.TransientModel):
    _name = 'stock.register.line'
    _description = 'Stock Register Line'

    report_id = fields.Many2one('stock.register.report', string='Report', ondelete='cascade')
    date = fields.Date(string='Date')
    reference = fields.Char(string='Reference')
    product_name = fields.Char(string='Product')
    sku = fields.Char(string='SKU')
    category = fields.Char(string='Category')
    quantity = fields.Float(string='Quantity')
    uom = fields.Char(string='UOM')
    source_location = fields.Char(string='Source Location')
    dest_location = fields.Char(string='Destination Location')
    status = fields.Char(string='Status')