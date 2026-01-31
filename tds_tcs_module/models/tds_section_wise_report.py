# models/tds_section_wise_report.py

from odoo import models, fields, api
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)

class TdsSectionWiseReport(models.Model):
    _name = 'tds.section.wise.report'
    _description = 'TDS Section-Wise Report'
    _order = 'date_from desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Report Name', required=True, default='Section-Wise TDS Report')
    date_from = fields.Date(string='From Date', required=True)
    date_to = fields.Date(string='To Date', required=True)
    partner_id = fields.Many2one('res.partner', string='Vendor')
    company_id = fields.Many2one('res.company', string='Company', 
                                  default=lambda self: self.env.company)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed')
    ], default='draft', string='Status')
    
    section_line_ids = fields.One2many('tds.section.wise.line', 'report_id', 
                                        string='Section-wise Summary')
    detail_line_ids = fields.One2many('tds.section.wise.detail', 'report_id', 
                                       string='Detailed Lines')
    
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
    section_count = fields.Integer(string='Section Count', compute='_compute_counts')
    transaction_count = fields.Integer(string='Transaction Count', compute='_compute_counts')

    @api.depends('section_line_ids', 'detail_line_ids')
    def _compute_counts(self):
        for record in self:
            record.section_count = len(record.section_line_ids)
            record.transaction_count = len(record.detail_line_ids)

    @api.depends('section_line_ids.taxable_amount', 'section_line_ids.tds_amount', 
                 'section_line_ids.invoice_amount')
    def _compute_totals(self):
        for record in self:
            record.total_taxable_amount = sum(record.section_line_ids.mapped('taxable_amount'))
            record.total_tds_amount = sum(record.section_line_ids.mapped('tds_amount'))
            record.total_invoice_amount = sum(record.section_line_ids.mapped('invoice_amount'))

    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        for record in self:
            if record.date_from > record.date_to:
                raise UserError("From Date cannot be greater than To Date!")

    def action_generate_report(self):
        """Generate Section-wise TDS Report"""
        self.ensure_one()
        
        # Clear existing lines
        self.section_line_ids.unlink()
        self.detail_line_ids.unlink()
        
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
        
        if self.company_id:
            domain.append(('company_id', '=', self.company_id.id))
        
        invoices = self.env['account.move'].search(domain, order='partner_id, invoice_date')
        
        _logger.info(f"Section-Wise Report: Found {len(invoices)} invoices")
        
        # Dictionary to store section-wise data
        section_data = {}
        detail_lines = []
        
        for invoice in invoices:
            partner = invoice.partner_id
            
            # Get TDS tax directly from partner's tds_tax_id field
            tds_tax = partner.tds_section_id.tds_tax_id
            
            if not tds_tax:
                _logger.warning(f"No tds_tax_id found for partner: {partner.name}")
                continue
            
            # Get TDS section
            tds_section = partner.tds_section_id
            if not tds_section:
                _logger.warning(f"No tds_section_id found for partner: {partner.name}")
                continue
            
            _logger.info(f"Processing invoice {invoice.name}, Partner: {partner.name}, Section: {tds_section.code}, Tax: {tds_tax.name}")
            
            # ---------------------------
            # Calculate Taxable Amount (Base Amount)
            # Filter invoice lines that have this TDS tax
            # ---------------------------
            tds_tax_lines = invoice.line_ids.filtered(
                lambda l: l.tax_line_id and l.tax_line_id.id == tds_tax.id
            )

            taxable_amount = abs(sum(tds_tax_lines.mapped('tax_base_amount')))
            tds_amount = abs(sum(tds_tax_lines.mapped('balance')))
            
            _logger.info(f"  Taxable lines: {len(tds_tax_lines)}, Amount: {taxable_amount}")
            
            # ---------------------------
            # Calculate TDS Amount (Tax Amount)
            # Filter journal entry lines where tax_line_id matches TDS tax
            # ---------------------------
            # tds_tax_lines = invoice.line_ids.filtered(
            #     lambda l: l.tax_line_id and l.tax_line_id.id == tds_tax.id
            # )
            # tds_amount = abs(sum(tds_tax_lines.mapped('balance')))
            
            _logger.info(f"  TDS tax lines: {len(tds_tax_lines)}, Amount: {tds_amount}")
            
            # Only process if there's TDS amount
            if tds_amount > 0:
                sign = 1 if invoice.move_type == 'in_invoice' else -1
                
                # Aggregate by section
                section_key = tds_section.id
                if section_key not in section_data:
                    section_data[section_key] = {
                        'section_id': tds_section.id,
                        'section_code': tds_section.code,
                        'section_name': tds_section.name,
                        'rate': tds_section.rate,
                        'vendor_count': set(),
                        'invoice_count': 0,
                        'taxable_amount': 0.0,
                        'tds_amount': 0.0,
                        'invoice_amount': 0.0,
                    }
                
                section_data[section_key]['vendor_count'].add(partner.id)
                section_data[section_key]['invoice_count'] += 1
                section_data[section_key]['taxable_amount'] += abs(taxable_amount) * sign
                section_data[section_key]['tds_amount'] += tds_amount * sign
                section_data[section_key]['invoice_amount'] += abs(invoice.amount_total) * sign
                
                # Get TDS rate
                tds_rate = partner.tds_rate if hasattr(partner, 'tds_rate') else tds_section.rate
                
                # Store detail line
                detail_lines.append({
                    'report_id': self.id,
                    'tds_section_id': tds_section.id,
                    'invoice_id': invoice.id,
                    'invoice_date': invoice.invoice_date,
                    'partner_id': partner.id,
                    'pan_number': partner.vat or '',
                    'tds_rate': tds_rate,
                    'taxable_amount': abs(taxable_amount) * sign,
                    'tds_amount': tds_amount * sign,
                    'invoice_amount': abs(invoice.amount_total) * sign,
                })
                
                _logger.info(f"  ✓ Added to section {tds_section.code}")
            else:
                _logger.warning(f"  ✗ Skipped - No TDS amount found")
        
        # Create section summary lines
        section_lines = []
        for section_id, data in section_data.items():
            section_lines.append({
                'report_id': self.id,
                'tds_section_id': data['section_id'],
                'vendor_count': len(data['vendor_count']),
                'invoice_count': data['invoice_count'],
                'taxable_amount': data['taxable_amount'],
                'tds_amount': data['tds_amount'],
                'invoice_amount': data['invoice_amount'],
            })
        
        if section_lines:
            self.env['tds.section.wise.line'].create(section_lines)
            self.env['tds.section.wise.detail'].create(detail_lines)
            self.state = 'confirmed'
            message = f'{len(section_lines)} section(s) with {len(detail_lines)} transaction(s) generated.'
            _logger.info(f"Section-Wise Report: {message}")
        else:
            message = 'No TDS entries found for the selected criteria.'
            _logger.warning(f"Section-Wise Report: {message}")
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Success' if section_lines else 'Information',
                'message': message,
                'type': 'success' if section_lines else 'warning',
                'sticky': False,
            }
        }

    def action_reset_to_draft(self):
        self.write({'state': 'draft'})

    def action_print_report(self):
        """Print Section-wise TDS Report"""
        self.ensure_one()
        if not self.section_line_ids:
            raise UserError("Please generate the report first before printing!")
        return self.env.ref('tds_tcs_module.action_report_tds_section_wise').report_action(self)

    def action_print_detailed_report(self):
        """Print Detailed Section-wise TDS Report"""
        self.ensure_one()
        if not self.detail_line_ids:
            raise UserError("Please generate the report first before printing!")
        return self.env.ref('tds_tcs_module.action_report_tds_section_wise_detailed').report_action(self)


class TdsSectionWiseLine(models.Model):
    _name = 'tds.section.wise.line'
    _description = 'TDS Section-Wise Summary Line'
    _order = 'tds_section_id'

    report_id = fields.Many2one('tds.section.wise.report', string='Report', 
                                 required=True, ondelete='cascade', index=True)
    tds_section_id = fields.Many2one('tds.section.master', string='TDS Section', 
                                      required=True, index=True)
    section_code = fields.Char(related='tds_section_id.code', string='Section Code', 
                                store=True, readonly=True)
    section_name = fields.Char(related='tds_section_id.name', string='Section Name', 
                                store=True, readonly=True)
    section_rate = fields.Float(related='tds_section_id.rate', string='Rate (%)', 
                                 store=True, readonly=True)
    vendor_count = fields.Integer(string='No. of Vendors')
    invoice_count = fields.Integer(string='No. of Invoices')
    taxable_amount = fields.Monetary(string='Total Taxable Amount', 
                                      currency_field='currency_id')
    tds_amount = fields.Monetary(string='Total TDS Amount', 
                                  currency_field='currency_id')
    invoice_amount = fields.Monetary(string='Total Invoice Amount', 
                                      currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', string='Currency',
                                   related='report_id.currency_id', readonly=True)

    def action_view_details(self):
        """View detailed transactions for this section"""
        self.ensure_one()
        return {
            'name': f'Details - {self.section_code}',
            'type': 'ir.actions.act_window',
            'res_model': 'tds.section.wise.detail',
            'view_mode': 'tree,form',
            'domain': [('report_id', '=', self.report_id.id), 
                      ('tds_section_id', '=', self.tds_section_id.id)],
            'context': {'create': False, 'delete': False}
        }


class TdsSectionWiseDetail(models.Model):
    _name = 'tds.section.wise.detail'
    _description = 'TDS Section-Wise Detail Line'
    _order = 'tds_section_id, invoice_date, partner_id'

    report_id = fields.Many2one('tds.section.wise.report', string='Report', 
                                 required=True, ondelete='cascade', index=True)
    tds_section_id = fields.Many2one('tds.section.master', string='TDS Section', 
                                      required=True, index=True)
    section_code = fields.Char(related='tds_section_id.code', string='Section Code', 
                                store=True, readonly=True)
    invoice_id = fields.Many2one('account.move', string='Invoice', required=True)
    invoice_number = fields.Char(related='invoice_id.name', string='Invoice Number', 
                                  store=True, readonly=True)
    invoice_date = fields.Date(string='Invoice Date', required=True, index=True)
    partner_id = fields.Many2one('res.partner', string='Vendor', required=True, index=True)
    pan_number = fields.Char(string='PAN Number')
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