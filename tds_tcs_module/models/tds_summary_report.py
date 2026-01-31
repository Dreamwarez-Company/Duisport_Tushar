# models/tds_summary_report.py

from odoo import models, fields, api
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)

class TdsSummaryReport(models.Model):
    _name = 'tds.summary.report'
    _description = 'TDS Summary Report - All Vendors'
    _order = 'date_from desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Report Name', required=True, default='TDS Summary Report')
    date_from = fields.Date(string='From Date', required=True, tracking=True)
    date_to = fields.Date(string='To Date', required=True, tracking=True)
    tds_section_id = fields.Many2one('tds.section.master', string='Filter by TDS Section')
    company_id = fields.Many2one('res.company', string='Company', 
                                  default=lambda self: self.env.company)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('generated', 'Generated'),
        ('printed', 'Printed')
    ], default='draft', string='Status', tracking=True)
    
    # Summary lines grouped by vendor
    vendor_summary_ids = fields.One2many('tds.summary.vendor', 'report_id', 
                                         string='Vendor Summary')
    
    # Detail lines - all invoices
    detail_line_ids = fields.One2many('tds.summary.detail', 'report_id', 
                                      string='Invoice Details')
    
    # Totals
    total_vendors = fields.Integer(string='Total Vendors', compute='_compute_totals', store=True)
    total_invoices = fields.Integer(string='Total Invoices', compute='_compute_totals', store=True)
    total_taxable_amount = fields.Monetary(string='Total Taxable Amount', 
                                           compute='_compute_totals', store=True,
                                           currency_field='currency_id')
    total_tds_amount = fields.Monetary(string='Total TDS Amount', 
                                        compute='_compute_totals', store=True,
                                        currency_field='currency_id')
    total_invoice_amount = fields.Monetary(string='Total Invoice Amount', 
                                            compute='_compute_totals', store=True,
                                            currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', string='Currency',
                                   related='company_id.currency_id', readonly=True)
    
    notes = fields.Text(string='Notes')

    @api.depends('vendor_summary_ids.taxable_amount', 'vendor_summary_ids.tds_amount', 
                 'vendor_summary_ids.invoice_amount', 'detail_line_ids')
    def _compute_totals(self):
        for record in self:
            record.total_vendors = len(record.vendor_summary_ids)
            record.total_invoices = len(record.detail_line_ids)
            record.total_taxable_amount = sum(record.vendor_summary_ids.mapped('taxable_amount'))
            record.total_tds_amount = sum(record.vendor_summary_ids.mapped('tds_amount'))
            record.total_invoice_amount = sum(record.vendor_summary_ids.mapped('invoice_amount'))

    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        for record in self:
            if record.date_from > record.date_to:
                raise UserError("From Date cannot be greater than To Date!")

    def action_generate_report(self):
        """Generate TDS Summary Report for All Vendors"""
        self.ensure_one()
        
        # Clear existing lines
        self.vendor_summary_ids.unlink()
        self.detail_line_ids.unlink()
        
        # Build domain
        domain = [
            ('move_type', 'in', ['in_invoice', 'in_refund']),
            ('state', '=', 'posted'),
            ('invoice_date', '>=', self.date_from),
            ('invoice_date', '<=', self.date_to),
            ('partner_id.tds_section_id.tds_tax_id', '!=', False),
        ]
        
        if self.tds_section_id:
            domain.append(('partner_id.tds_section_id', '=', self.tds_section_id.id))
        
        if self.company_id:
            domain.append(('company_id', '=', self.company_id.id))
        
        invoices = self.env['account.move'].search(domain, order='partner_id, invoice_date')
        
        _logger.info(f"TDS Summary Report: Found {len(invoices)} invoices")
        
        # Dictionary to store vendor-wise data
        vendor_data = {}
        detail_lines = []
        
        for invoice in invoices:
            partner = invoice.partner_id
            
            # Get TDS tax
            tds_tax = partner.tds_section_id.tds_tax_id
            if not tds_tax:
                _logger.warning(f"No tds_tax_id for partner: {partner.name}")
                continue
            
            # Get TDS section
            tds_section = partner.tds_section_id
            
            tds_tax_lines = invoice.line_ids.filtered(
                lambda l: l.tax_line_id and l.tax_line_id.id == tds_tax.id
            )

            taxable_amount = abs(sum(tds_tax_lines.mapped('tax_base_amount')))
            tds_amount = abs(sum(tds_tax_lines.mapped('balance')))
            
            tds_amount = abs(sum(tds_tax_lines.mapped('balance')))
            
            if tds_amount > 0 or taxable_amount > 0:
                sign = 1 if invoice.move_type == 'in_invoice' else -1
                
                # Aggregate by vendor
                vendor_key = partner.id
                if vendor_key not in vendor_data:
                    vendor_data[vendor_key] = {
                        'partner_id': partner.id,
                        'partner_name': partner.name,
                        'pan_number': partner.vat or '',
                        'tds_section_id': tds_section.id if tds_section else False,
                        'tds_section_code': tds_section.code if tds_section else '',
                        'tds_rate': partner.tds_rate if hasattr(partner, 'tds_rate') else (tds_section.rate if tds_section else 0.0),
                        'invoice_count': 0,
                        'taxable_amount': 0.0,
                        'tds_amount': 0.0,
                        'invoice_amount': 0.0,
                    }
                
                vendor_data[vendor_key]['invoice_count'] += 1
                vendor_data[vendor_key]['taxable_amount'] += abs(taxable_amount) * sign
                vendor_data[vendor_key]['tds_amount'] += tds_amount * sign
                vendor_data[vendor_key]['invoice_amount'] += abs(invoice.amount_total) * sign
                
                # Store detail line
                detail_lines.append({
                    'report_id': self.id,
                    'partner_id': partner.id,
                    'invoice_id': invoice.id,
                    'invoice_date': invoice.invoice_date,
                    'pan_number': partner.vat or '',
                    'tds_section_id': tds_section.id if tds_section else False,
                    'tds_rate': partner.tds_rate if hasattr(partner, 'tds_rate') else (tds_section.rate if tds_section else 0.0),
                    'taxable_amount': abs(taxable_amount) * sign,
                    'tds_amount': tds_amount * sign,
                    'invoice_amount': abs(invoice.amount_total) * sign,
                })
        
        # Create vendor summary lines
        vendor_lines = []
        for vendor_id, data in vendor_data.items():
            vendor_lines.append({
                'report_id': self.id,
                'partner_id': data['partner_id'],
                'pan_number': data['pan_number'],
                'tds_section_id': data['tds_section_id'],
                'tds_rate': data['tds_rate'],
                'invoice_count': data['invoice_count'],
                'taxable_amount': data['taxable_amount'],
                'tds_amount': data['tds_amount'],
                'invoice_amount': data['invoice_amount'],
            })
        
        if vendor_lines:
            self.env['tds.summary.vendor'].create(vendor_lines)
            self.env['tds.summary.detail'].create(detail_lines)
            self.state = 'generated'
            message = f'{len(vendor_lines)} vendor(s) with {len(detail_lines)} invoice(s) generated.'
            _logger.info(f"TDS Summary Report: {message}")
        else:
            message = 'No TDS entries found for the selected criteria.'
            _logger.warning(f"TDS Summary Report: {message}")
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Success' if vendor_lines else 'Information',
                'message': message,
                'type': 'success' if vendor_lines else 'warning',
                'sticky': False,
            }
        }

    def action_reset_to_draft(self):
        self.write({'state': 'draft'})

    def action_print_summary(self):
        """Print Vendor Summary Report"""
        self.ensure_one()
        if not self.vendor_summary_ids:
            raise UserError("Please generate the report first before printing!")
        self.write({'state': 'printed'})
        return self.env.ref('tds_tcs_module.action_report_tds_summary').report_action(self)

    def action_print_detailed(self):
        """Print Detailed Report with All Invoices"""
        self.ensure_one()
        if not self.detail_line_ids:
            raise UserError("Please generate the report first before printing!")
        self.write({'state': 'printed'})
        return self.env.ref('tds_tcs_module.action_report_tds_summary_detailed').report_action(self)


class TdsSummaryVendor(models.Model):
    _name = 'tds.summary.vendor'
    _description = 'TDS Summary - Vendor Wise'
    _order = 'partner_id'

    report_id = fields.Many2one('tds.summary.report', string='Report', 
                                 required=True, ondelete='cascade', index=True)
    partner_id = fields.Many2one('res.partner', string='Vendor', required=True, index=True)
    pan_number = fields.Char(string='PAN Number')
    tds_section_id = fields.Many2one('tds.section.master', string='TDS Section')
    tds_section_code = fields.Char(related='tds_section_id.code', string='Section Code', store=True)
    tds_rate = fields.Float(string='TDS Rate (%)')
    invoice_count = fields.Integer(string='No. of Invoices')
    taxable_amount = fields.Monetary(string='Total Taxable Amount', currency_field='currency_id')
    tds_amount = fields.Monetary(string='Total TDS Amount', currency_field='currency_id')
    invoice_amount = fields.Monetary(string='Total Invoice Amount', currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', string='Currency',
                                   related='report_id.currency_id', readonly=True)

    def action_view_invoices(self):
        """View all invoices for this vendor"""
        self.ensure_one()
        return {
            'name': f'Invoices - {self.partner_id.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'tds.summary.detail',
            'view_mode': 'tree,form',
            'domain': [('report_id', '=', self.report_id.id), 
                      ('partner_id', '=', self.partner_id.id)],
            'context': {'create': False, 'delete': False}
        }


class TdsSummaryDetail(models.Model):
    _name = 'tds.summary.detail'
    _description = 'TDS Summary - Invoice Details'
    _order = 'partner_id, invoice_date'

    report_id = fields.Many2one('tds.summary.report', string='Report', 
                                 required=True, ondelete='cascade', index=True)
    partner_id = fields.Many2one('res.partner', string='Vendor', required=True, index=True)
    invoice_id = fields.Many2one('account.move', string='Invoice', required=True)
    invoice_number = fields.Char(related='invoice_id.name', string='Invoice Number', store=True)
    invoice_date = fields.Date(string='Invoice Date', required=True, index=True)
    pan_number = fields.Char(string='PAN Number')
    tds_section_id = fields.Many2one('tds.section.master', string='TDS Section')
    tds_section_code = fields.Char(related='tds_section_id.code', string='Section Code', store=True)
    tds_rate = fields.Float(string='TDS Rate (%)')
    taxable_amount = fields.Monetary(string='Taxable Amount', currency_field='currency_id')
    tds_amount = fields.Monetary(string='TDS Amount', currency_field='currency_id')
    invoice_amount = fields.Monetary(string='Invoice Amount', currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', string='Currency',
                                   related='report_id.currency_id', readonly=True)

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