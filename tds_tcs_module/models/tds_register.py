# models/tds_register.py
from odoo import models, fields, api
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)

class TdsRegister(models.Model):
    _name = 'tds.register'
    _description = 'TDS Register'
    _order = 'date_from desc'
    
    name = fields.Char(string='Register Name', required=True, default='TDS Register')
    date_from = fields.Date(string='From Date', required=True)
    date_to = fields.Date(string='To Date', required=True)
    partner_id = fields.Many2one('res.partner', string='Vendor')
    tds_section_id = fields.Many2one('tds.section.master', string='TDS Section')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed')
    ], default='draft', string='Status')
    
    line_ids = fields.One2many('tds.register.line', 'register_id', string='TDS Lines')
    
    total_taxable_amount = fields.Float(string='Total Taxable Amount', compute='_compute_totals', store=True)
    total_tds_amount = fields.Float(string='Total TDS Amount', compute='_compute_totals', store=True)
    total_invoice_amount = fields.Float(string='Total Invoice Amount', compute='_compute_totals', store=True)
    
    @api.depends('line_ids.taxable_amount', 'line_ids.tds_amount', 'line_ids.invoice_amount')
    def _compute_totals(self):
        for record in self:
            record.total_taxable_amount = sum(record.line_ids.mapped('taxable_amount'))
            record.total_tds_amount = sum(record.line_ids.mapped('tds_amount'))
            record.total_invoice_amount = sum(record.line_ids.mapped('invoice_amount'))
    
    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        for record in self:
            if record.date_from > record.date_to:
                raise UserError("From Date cannot be greater than To Date!")
    
    def action_generate_report(self):
        """Generate TDS Register Report"""
        self.ensure_one()
        
        # Clear existing lines
        self.line_ids.unlink()
        
        # Build domain - looking for vendors with tds_tax_id
        domain = [
            ('move_type', 'in', ['in_invoice', 'in_refund']),
            ('state', '=', 'posted'),
            ('invoice_date', '>=', self.date_from),
            ('invoice_date', '<=', self.date_to),
            ('partner_id.tds_section_id.tds_tax_id', '!=', False),  # Filter by tds_tax_id field
        ]
        
        if self.partner_id:
            domain.append(('partner_id', '=', self.partner_id.id))
        
        if self.tds_section_id:
            domain.append(('partner_id.tds_section_id', '=', self.tds_section_id.id))
        
        vendor_bills = self.env['account.move'].search(domain, order='invoice_date, partner_id')
        
        _logger.info(f"TDS Register: Found {len(vendor_bills)} vendor bills")
        
        lines_data = []
        
        for bill in vendor_bills:
            partner = bill.partner_id
            
            # Get TDS tax directly from partner's tds_tax_id field
            tds_tax = partner.tds_section_id.tds_tax_id
            
            if not tds_tax:
                _logger.warning(f"No tds_tax_id found for partner: {partner.name}")
                continue
            
            _logger.info(f"Processing bill {bill.name} for partner {partner.name}, TDS Tax: {tds_tax.name}")
            
            # ---------------------------
            # Calculate Taxable Amount (Base Amount)
            # Filter invoice lines that have this TDS tax
            # ---------------------------
            tds_tax_lines = bill.line_ids.filtered(
                lambda l: l.tax_line_id and l.tax_line_id.id == tds_tax.id
            )

            taxable_amount = sum(tds_tax_lines.mapped('tax_base_amount'))
            
            _logger.info(f"  Found {len(tds_tax_lines)} tax lines, Taxable Amount: {taxable_amount}")
            
            # ---------------------------
            # Calculate TDS Amount (Tax Amount)
            # Filter journal entry lines where tax_line_id matches TDS tax
            # ---------------------------
            tds_tax_lines = bill.line_ids.filtered(
                lambda l: l.tax_line_id and l.tax_line_id.id == tds_tax.id
            )
            tds_amount = abs(sum(tds_tax_lines.mapped('balance')))
            
            _logger.info(f"  Found {len(tds_tax_lines)} tax lines, TDS Amount: {tds_amount}")
            
            # ---------------------------
            # Create register line if amounts exist
            # ---------------------------
            if taxable_amount > 0 or tds_amount > 0:
                sign = 1 if bill.move_type == 'in_invoice' else -1
                
                # Get TDS section and rate
                tds_section = partner.tds_section_id if partner.tds_section_id else None
                tds_rate = partner.tds_rate if hasattr(partner, 'tds_rate') else (tds_section.rate if tds_section else 0.0)
                
                lines_data.append({
                    'register_id': self.id,
                    'invoice_id': bill.id,
                    'invoice_date': bill.invoice_date,
                    'partner_id': partner.id,
                    'pan_number': partner.vat or '',
                    'tds_section_id': tds_section.id if tds_section else False,
                    'tds_rate': tds_rate,
                    'taxable_amount': abs(taxable_amount) * sign,
                    'tds_amount': tds_amount * sign,
                    'invoice_amount': abs(bill.amount_total) * sign,
                })
                
                _logger.info(f"  ✓ Added line for bill {bill.name}")
        
        if lines_data:
            self.env['tds.register.line'].create(lines_data)
            self.state = 'confirmed'
            message = f'{len(lines_data)} vendor bill TDS entries generated successfully.'
            _logger.info(f"TDS Register: {message}")
        else:
            message = 'No TDS entries found for the selected criteria.'
            _logger.warning(f"TDS Register: {message}")
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Success' if lines_data else 'Information',
                'message': message,
                'type': 'success' if lines_data else 'warning',
                'sticky': False,
            }
        }
    
    def action_reset_to_draft(self):
        self.write({'state': 'draft'})
    
    def action_print_report(self):
        self.ensure_one()
        if not self.line_ids:
            raise UserError("Please generate the report first before printing!")
        return self.env.ref('tds_tcs_module.action_report_tds_register').report_action(self)


class TdsRegisterLine(models.Model):
    _name = 'tds.register.line'
    _description = 'TDS Register Line'
    _order = 'invoice_date, partner_id'
    
    register_id = fields.Many2one('tds.register', string='TDS Register', required=True, ondelete='cascade')
    invoice_id = fields.Many2one('account.move', string='Invoice', required=True)
    invoice_number = fields.Char(related='invoice_id.name', string='Invoice Number', store=True)
    invoice_date = fields.Date(string='Invoice Date', required=True)
    partner_id = fields.Many2one('res.partner', string='Vendor', required=True)
    pan_number = fields.Char(string='PAN Number')
    tds_section_id = fields.Many2one('tds.section.master', string='TDS Section')
    tds_rate = fields.Float(string='TDS Rate (%)')
    taxable_amount = fields.Float(string='Taxable Amount')
    tds_amount = fields.Float(string='TDS Amount')
    invoice_amount = fields.Float(string='Invoice Amount')
    
    tds_section_code = fields.Char(related='tds_section_id.code', string='Section Code', store=True)
    
    def action_view_invoice(self):
        """Open related invoice"""
        self.ensure_one()
        return {
            'name': 'Invoice',
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'form',
            'res_id': self.invoice_id.id,
            'context': {'create': False}
        }