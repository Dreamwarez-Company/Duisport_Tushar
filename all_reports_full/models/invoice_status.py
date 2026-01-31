from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)


class InvoiceStatusWizard(models.TransientModel):
    _name = 'invoice.status.wizard'
    _description = 'Invoice Status Report Wizard'

    date_from = fields.Date(string='Date From', required=False, 
                            default=lambda self: fields.Date.today())
    date_to = fields.Date(string='Date To', required=False, 
                          default=lambda self: fields.Date.today())
    partner_ids = fields.Many2many('res.partner', string='Customers')
    invoice_type = fields.Selection([
        ('out_invoice', 'Customer Invoices'),
        ('in_invoice', 'Vendor Bills'),
        ('out_refund', 'Customer Credit Notes'),
        ('in_refund', 'Vendor Credit Notes'),
        ('all', 'All Types')
    ], string='Invoice Type', default='out_invoice', required=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('posted', 'Posted'),
        ('cancel', 'Cancelled'),
        ('all', 'All States')
    ], string='Status', default='all', required=True)
    payment_state = fields.Selection([
        ('not_paid', 'Not Paid'),
        ('in_payment', 'In Payment'),
        ('paid', 'Paid'),
        ('partial', 'Partially Paid'),
        ('reversed', 'Reversed'),
        ('invoicing_legacy', 'Invoicing App Legacy'),
        ('all', 'All Payment States')
    ], string='Payment Status', default='all')

    def print_report(self):
        self.ensure_one()
        data = {
            'ids': self.ids,
            'model': self._name,
            'form': {
                'date_from': self.date_from.strftime('%Y-%m-%d') if self.date_from else False,
                'date_to': self.date_to.strftime('%Y-%m-%d') if self.date_to else False,
                'partner_ids': self.partner_ids.ids,
                'invoice_type': self.invoice_type,
                'state': self.state,
                'payment_state': self.payment_state,
            }
        }
        return self.env.ref('all_reports_full.action_invoice_status_report').report_action(self, data=data)


class InvoiceStatusReport(models.AbstractModel):
    _name = 'report.all_reports_full.invoice_status_template'
    _description = 'Invoice Status Report'

    def _safe_sum(self, recordset, field_name):
        """Safely sum a field, returning 0.0 if empty or None"""
        try:
            if not recordset:
                return 0.0
            result = sum(recordset.mapped(field_name))
            return result if result is not None else 0.0
        except:
            return 0.0

    @api.model
    def _get_report_values(self, docids, data=None):
        _logger.info("#"*80)
        _logger.info("INVOICE STATUS REPORT - _get_report_values CALLED")
        _logger.info(f"docids: {docids}")
        _logger.info(f"data: {data}")
        
        # Get wizard data
        if data and data.get('form'):
            form_data = data['form']
            date_from = form_data.get('date_from')
            date_to = form_data.get('date_to')
            partner_ids = form_data.get('partner_ids', [])
            invoice_type = form_data.get('invoice_type', 'out_invoice')
            state = form_data.get('state', 'all')
            payment_state = form_data.get('payment_state', 'all')
            _logger.info("Data source: FORM DATA")
        else:
            wizard = self.env['invoice.status.wizard'].browse(docids)
            if wizard:
                date_from = wizard.date_from.strftime('%Y-%m-%d') if wizard.date_from else False
                date_to = wizard.date_to.strftime('%Y-%m-%d') if wizard.date_to else False
                partner_ids = wizard.partner_ids.ids
                invoice_type = wizard.invoice_type
                state = wizard.state
                payment_state = wizard.payment_state
                _logger.info("Data source: WIZARD BROWSE")
            else:
                date_from = fields.Date.today().strftime('%Y-%m-%d')
                date_to = fields.Date.today().strftime('%Y-%m-%d')
                partner_ids = []
                invoice_type = 'all'
                state = 'all'
                payment_state = 'all'
                _logger.info("Data source: DEFAULT")
        
        _logger.info(f"Parsed Date From: {date_from}")
        _logger.info(f"Parsed Date To: {date_to}")
        _logger.info(f"Parsed Invoice Type: {invoice_type}")
        _logger.info(f"Parsed State: {state}")
        _logger.info(f"Parsed Payment State: {payment_state}")
        
        # Build simple domain
        domain = []
        
        # Invoice type filter
        if invoice_type == 'out_invoice':
            domain.append(('move_type', '=', 'out_invoice'))
        elif invoice_type == 'in_invoice':
            domain.append(('move_type', '=', 'in_invoice'))
        elif invoice_type == 'out_refund':
            domain.append(('move_type', '=', 'out_refund'))
        elif invoice_type == 'in_refund':
            domain.append(('move_type', '=', 'in_refund'))
        else:
            domain.append(('move_type', 'in', ['out_invoice', 'in_invoice', 'out_refund', 'in_refund']))
        
        _logger.info(f"Domain after invoice_type: {domain}")
        
        # State filter
        if state and state != 'all':
            domain.append(('state', '=', state))
            _logger.info(f"Added state filter: {state}")
        
        # Payment state filter
        if payment_state and payment_state != 'all':
            domain.append(('payment_state', '=', payment_state))
            _logger.info(f"Added payment_state filter: {payment_state}")
        
        # Partner filter
        if partner_ids:
            domain.append(('partner_id', 'in', partner_ids))
            _logger.info(f"Added partner filter: {partner_ids}")
        
        # Date filter - try both fields
        if date_from:
            domain.append('|')
            domain.append(('invoice_date', '>=', date_from))
            domain.append('&')
            domain.append(('invoice_date', '=', False))
            domain.append(('date', '>=', date_from))
            _logger.info(f"Added date_from filter: {date_from}")
        
        if date_to:
            domain.append('|')
            domain.append(('invoice_date', '<=', date_to))
            domain.append('&')
            domain.append(('invoice_date', '=', False))
            domain.append(('date', '<=', date_to))
            _logger.info(f"Added date_to filter: {date_to}")
        
        _logger.info(f"FINAL DOMAIN: {domain}")
        
        # Get invoices
        invoices = self.env['account.move'].search(domain, order='date desc, name')
        _logger.info(f"FOUND {len(invoices)} INVOICES")
        
        if invoices:
            _logger.info("SAMPLE INVOICES:")
            for inv in invoices[:5]:  # Show first 5
                _logger.info(f"  - {inv.name}: Date={inv.invoice_date}, Type={inv.move_type}, State={inv.state}, Payment={inv.payment_state}")
        else:
            _logger.info("NO INVOICES FOUND - Let's check total invoices in system:")
            all_invoices = self.env['account.move'].search([('move_type', 'in', ['out_invoice', 'in_invoice', 'out_refund', 'in_refund'])], limit=10)
            _logger.info(f"Total invoices in system (sample of 10): {len(all_invoices)}")
            for inv in all_invoices:
                _logger.info(f"  - {inv.name}: Date={inv.invoice_date}, Type={inv.move_type}, State={inv.state}")
        
        _logger.info("#"*80)
        
        # Group invoices by status
        draft_invoices = invoices.filtered(lambda inv: inv.state == 'draft')
        posted_invoices = invoices.filtered(lambda inv: inv.state == 'posted')
        cancelled_invoices = invoices.filtered(lambda inv: inv.state == 'cancel')
        
        # Group by payment state
        not_paid = invoices.filtered(lambda inv: inv.payment_state == 'not_paid')
        partial_paid = invoices.filtered(lambda inv: inv.payment_state == 'partial')
        paid = invoices.filtered(lambda inv: inv.payment_state == 'paid')
        
        # Calculate totals using safe sum
        total_draft = self._safe_sum(draft_invoices, 'amount_total')
        total_posted = self._safe_sum(posted_invoices, 'amount_total')
        total_cancelled = self._safe_sum(cancelled_invoices, 'amount_total')
        total_not_paid = self._safe_sum(not_paid, 'amount_residual')
        total_paid = self._safe_sum(paid, 'amount_total')
        total_partial = self._safe_sum(partial_paid, 'amount_residual')
        
        # Overall totals
        grand_total = self._safe_sum(invoices, 'amount_total')
        total_due = self._safe_sum(invoices, 'amount_residual')
        
        # Group by customer
        customer_summary = []
        if invoices:
            customer_dict = {}
            for invoice in invoices:
                partner = invoice.partner_id
                if partner:
                    if partner.id not in customer_dict:
                        customer_dict[partner.id] = {
                            'partner_name': partner.name or 'Unknown',
                            'invoice_count': 0,
                            'total_amount': 0.0,
                            'total_due': 0.0,
                        }
                    customer_dict[partner.id]['invoice_count'] += 1
                    customer_dict[partner.id]['total_amount'] += (invoice.amount_total or 0.0)
                    customer_dict[partner.id]['total_due'] += (invoice.amount_residual or 0.0)
            
            # Convert to list and sort
            customer_summary = sorted(customer_dict.values(), 
                                    key=lambda x: x['total_amount'], reverse=True)
        
        # Get invoice type label
        invoice_type_labels = {
            'out_invoice': 'Customer Invoices',
            'in_invoice': 'Vendor Bills',
            'out_refund': 'Customer Credit Notes',
            'in_refund': 'Vendor Credit Notes',
            'all': 'All Types'
        }
        
        # State labels
        state_label = state.replace('_', ' ').title() if state else 'All'
        payment_state_label = payment_state.replace('_', ' ').title() if payment_state else 'All'
        
        return {
            'doc_ids': docids,
            'doc_model': 'invoice.status.wizard',
            'date_from': str(date_from) if date_from else '',
            'date_to': str(date_to) if date_to else '',
            'invoice_type': invoice_type or 'all',
            'invoice_type_label': invoice_type_labels.get(invoice_type, 'All Types'),
            'state_filter': state or 'all',
            'payment_state_filter': payment_state or 'all',
            'state_label': state_label,
            'payment_state_label': payment_state_label,
            'invoices': invoices,
            'invoice_count': len(invoices),
            'draft_invoices': draft_invoices,
            'draft_count': len(draft_invoices),
            'posted_invoices': posted_invoices,
            'posted_count': len(posted_invoices),
            'cancelled_invoices': cancelled_invoices,
            'cancelled_count': len(cancelled_invoices),
            'not_paid': not_paid,
            'not_paid_count': len(not_paid),
            'partial_paid': partial_paid,
            'partial_count': len(partial_paid),
            'paid': paid,
            'paid_count': len(paid),
            'total_draft': float(total_draft),
            'total_posted': float(total_posted),
            'total_cancelled': float(total_cancelled),
            'total_not_paid': float(total_not_paid),
            'total_paid': float(total_paid),
            'total_partial': float(total_partial),
            'grand_total': float(grand_total),
            'total_due': float(total_due),
            'customer_summary': customer_summary,
            'company_name': self.env.company.name or 'Company',
        }