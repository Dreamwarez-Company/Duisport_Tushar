# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError
import io, base64

try:
    import xlsxwriter
except Exception:
    xlsxwriter = None

class MaterialConsumptionReport(models.TransientModel):
    _name = 'material.consumption.report'
    _description = 'Material Consumption Report'
    

    date_from = fields.Date(string='From Date', required=True)
    date_to = fields.Date(string='To Date', required=True)
    product_id = fields.Many2one('product.product', string='Product')
    categ_id = fields.Many2one('product.category', string='Product Category')
    line_ids = fields.One2many('material.consumption.line', 'report_id', string='Lines')

    def action_view_report(self):
        """Fetch and display report data"""
        self.line_ids.unlink()
        
        # Build domain for stock moves
        domain = [
            ('date', '>=', self.date_from),
            ('date', '<=', self.date_to),
            ('state', '=', 'done'),
            ('location_id.usage', '=', 'internal'),
        ]
        
        # Filter by product
        if self.product_id:
            domain.append(('product_id', '=', self.product_id.id))
        elif self.categ_id:
            # Get all products in category
            products = self.env['product.product'].search([
                ('categ_id', 'child_of', self.categ_id.id)
            ])
            domain.append(('product_id', 'in', products.ids))
        
        # Get consumed moves (moved out from internal locations)
        moves = self.env['stock.move'].search(domain)
        
        lines_to_create = []
        for move in moves:
            # Determine where the product was used
            used_in = ''
            reference = ''
            
            if move.raw_material_production_id:
                # Used in manufacturing
                used_in = 'Manufacturing Order'
                reference = move.raw_material_production_id.name
                product_produced = move.raw_material_production_id.product_id.name
            elif move.location_dest_id.usage == 'production':
                used_in = 'Production'
                reference = move.reference or move.picking_id.name if move.picking_id else ''
                product_produced = 'Production Location'
            elif move.location_dest_id.usage == 'customer':
                used_in = 'Customer Delivery'
                reference = move.picking_id.name if move.picking_id else move.reference or ''
                product_produced = move.partner_id.name if move.partner_id else 'Customer'
            elif move.location_dest_id.usage == 'inventory':
                used_in = 'Inventory Adjustment'
                reference = move.reference or ''
                product_produced = 'Adjustment'
            else:
                used_in = f'{move.location_dest_id.name}'
                reference = move.reference or move.picking_id.name if move.picking_id else ''
                product_produced = move.location_dest_id.complete_name
            
            lines_to_create.append({
                'report_id': self.id,
                'date': move.date,
                'product_name': move.product_id.name,
                'product_code': move.product_id.default_code or '',
                'category': move.product_id.categ_id.name if move.product_id.categ_id else '',
                'quantity': move.product_uom_qty,
                'uom': move.product_uom.name,
                'used_in': used_in,
                'reference': reference,
                'produced_product': product_produced,
                'source_location': move.location_id.complete_name,
                'dest_location': move.location_dest_id.complete_name,
            })
        
        self.env['material.consumption.line'].create(lines_to_create)
        
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'material.consumption.report',
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
        sheet = workbook.add_worksheet('Material Consumption')
        
        # Headers
        headers = ['Date', 'Product', 'Code', 'Category', 'Quantity', 'UOM', 
                   'Used In', 'Reference', 'For Product/Location', 'Source', 'Destination']
        for col, h in enumerate(headers):
            sheet.write(0, col, h)
        
        # Data
        row = 1
        for line in self.line_ids:
            sheet.write(row, 0, str(line.date))
            sheet.write(row, 1, line.product_name)
            sheet.write(row, 2, line.product_code)
            sheet.write(row, 3, line.category)
            sheet.write(row, 4, float(line.quantity))
            sheet.write(row, 5, line.uom)
            sheet.write(row, 6, line.used_in)
            sheet.write(row, 7, line.reference)
            sheet.write(row, 8, line.produced_product)
            sheet.write(row, 9, line.source_location)
            sheet.write(row, 10, line.dest_location)
            row += 1
        
        workbook.close()
        
        attachment = self.env['ir.attachment'].create({
            'name': f'material_consumption_{self.date_from}_{self.date_to}.xlsx',
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
        return self.env.ref('all_reports_full.report_material_consumption_pdf').report_action(self)


class MaterialConsumptionLine(models.TransientModel):
    _name = 'material.consumption.line'
    _description = 'Material Consumption Line'

    report_id = fields.Many2one('material.consumption.report', string='Report', ondelete='cascade')
    date = fields.Datetime(string='Date')
    product_name = fields.Char(string='Product')
    product_code = fields.Char(string='Product Code')
    category = fields.Char(string='Category')
    quantity = fields.Float(string='Quantity')
    uom = fields.Char(string='UOM')
    used_in = fields.Char(string='Used In')
    reference = fields.Char(string='Reference')
    produced_product = fields.Char(string='For Product/Location')
    source_location = fields.Char(string='Source Location')
    dest_location = fields.Char(string='Destination Location')