# -*- coding: utf-8 -*-
from odoo import models, fields, api

class StockValuationReportWizard(models.TransientModel):
    _name = 'stock.valuation.report.wizard'
    _description = 'Stock Valuation Report Wizard'

    date_from = fields.Date(
        string='Date From',
        required=True,
        default=fields.Date.context_today
    )
    date_to = fields.Date(
        string='Date To',
        required=True,
        default=fields.Date.context_today
    )
    product_ids = fields.Many2many(
        'product.product',
        string='Products',
        help='Leave empty to include all products'
    )
    categ_ids = fields.Many2many(
        'product.category',
        string='Product Categories',
        help='Leave empty to include all categories'
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company
    )
    
    # Fields to display report data in wizard
    report_line_ids = fields.One2many(
        'stock.valuation.report.line',
        'wizard_id',
        string='Report Lines',
        readonly=True
    )

    def _compute_move_value(self, move):
        """Calculate the value of a stock move"""
        value = 0.0
        quantity = 0.0
        
        # Determine if it's incoming or outgoing
        is_incoming = move.location_dest_id.usage == 'internal' and move.location_id.usage != 'internal'
        is_outgoing = move.location_id.usage == 'internal' and move.location_dest_id.usage != 'internal'
        
        # Calculate quantity with sign
        if is_outgoing:
            quantity = -move.product_qty
        else:
            quantity = move.product_qty
        
        # Try to get value from valuation layers first (for automated valuation)
        if move.stock_valuation_layer_ids:
            value = sum(move.stock_valuation_layer_ids.mapped('value'))
        # Check if linked to sale order line (outgoing)
        elif move.sale_line_id:
            value = -move.sale_line_id.price_subtotal
        # Check if linked to purchase order line (incoming)
        elif move.purchase_line_id:
            value = move.purchase_line_id.price_subtotal
        # Fallback to product standard price
        else:
            if is_outgoing:
                value = -move.product_qty * move.product_id.standard_price
            elif is_incoming:
                # Try to get price from move's price_unit
                value = move.product_qty * (move.price_unit or move.product_id.standard_price)
            else:
                # Internal move
                value = 0.0
        
        return quantity, value

    def action_generate_report(self):
        """Generate report data and display in wizard"""
        self.ensure_one()
        
        # Clear existing lines
        self.report_line_ids.unlink()
        
        # Get report data
        domain = self._get_report_domain()
        moves = self.env['stock.move'].search(domain, order='product_id, date desc')
        
        # Create report lines
        lines_to_create = []
        for move in moves:
            qty, value = self._compute_move_value(move)
            
            lines_to_create.append({
                'wizard_id': self.id,
                'date': move.date,
                'reference': move.reference or move.picking_id.name or move.name,
                'product_id': move.product_id.id,
                'company_id': move.company_id.id,
                'quantity': qty,
                'uom_id': move.product_id.uom_id.id,
                'value': value,
            })
        
        if lines_to_create:
            self.env['stock.valuation.report.line'].create(lines_to_create)
        
        # Return action to reload wizard with report data
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'stock.valuation.report.wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }

    def action_print_report(self):
        """Print PDF report"""
        self.ensure_one()
        return self.env.ref('all_reports_full.action_report_stock_valuation').report_action(self)

    def _get_report_domain(self):
        """Build domain for filtering stock moves"""
        domain = [
            ('date', '>=', self.date_from),
            ('date', '<=', self.date_to),
            ('state', '=', 'done'),
            ('company_id', '=', self.company_id.id),
        ]
        
        if self.product_ids:
            domain.append(('product_id', 'in', self.product_ids.ids))
        
        if self.categ_ids:
            domain.append(('product_id.categ_id', 'in', self.categ_ids.ids))
        
        return domain

    def _get_report_data(self):
        """Get data for the report - used for PDF generation"""
        domain = self._get_report_domain()
        moves = self.env['stock.move'].search(domain, order='date desc, product_id')
        
        # Group data by product
        product_data = {}
        for move in moves:
            product = move.product_id
            if product.id not in product_data:
                product_data[product.id] = {
                    'product': product,
                    'moves': [],
                    'total_qty': 0.0,
                    'total_value': 0.0,
                }
            
            qty, value = self._compute_move_value(move)
            
            product_data[product.id]['moves'].append({
                'date': move.date,
                'reference': move.reference or move.picking_id.name or move.name,
                'product': product.name,
                'company': move.company_id.name,
                'quantity': qty,
                'uom': product.uom_id.name,
                'value': value,
            })
            product_data[product.id]['total_qty'] += qty
            product_data[product.id]['total_value'] += value
        
        return product_data


class StockValuationReportLine(models.TransientModel):
    _name = 'stock.valuation.report.line'
    _description = 'Stock Valuation Report Line'
    _order = 'product_id, date desc'

    wizard_id = fields.Many2one(
        'stock.valuation.report.wizard',
        string='Wizard',
        required=True,
        ondelete='cascade'
    )
    date = fields.Datetime(string='Date')
    reference = fields.Char(string='Reference')
    product_id = fields.Many2one('product.product', string='Product')
    company_id = fields.Many2one('res.company', string='Company')
    quantity = fields.Float(string='Moved Quantity', digits='Product Unit of Measure')
    uom_id = fields.Many2one('uom.uom', string='Unit of Measure')
    value = fields.Monetary(string='Total Value', currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id', string='Currency')