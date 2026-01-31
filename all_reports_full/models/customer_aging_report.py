# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError
import io, base64
from datetime import date

try:
    import xlsxwriter
except Exception:
    xlsxwriter = None

class CustomerAgingReport(models.TransientModel):
    _name = 'customer.aging.report'
    _description = 'Customer Aging Report'

    end_date = fields.Date(string='As of Date', required=True)
    partner_id = fields.Many2one('res.partner', string='Customer', domain=[('customer_rank', '>', 0)])
    line_ids = fields.One2many('customer.aging.line', 'report_id', string='Lines')

    def action_view_report(self):
        """Fetch and display report data"""
        self.line_ids.unlink()
        
        domain = [
            ('date', '<=', self.end_date),
            ('reconciled', '=', False),
            ('parent_state', '=', 'posted'),
            ('account_id.account_type', '=', 'asset_receivable')
        ]
        
        # Add partner filter if customer is selected
        if self.partner_id:
            domain.append(('partner_id', '=', self.partner_id.id))
        
        lines = self.env['account.move.line'].search(domain)
        partners = {}
        for l in lines:
            partner = l.partner_id
            if not partner:
                continue
            partners.setdefault(partner.id, []).append(l)
        
        lines_to_create = []
        for pid, lns in partners.items():
            partner = self.env['res.partner'].browse(pid)
            buckets = [0, 0, 0, 0, 0, 0]  # 0-30, 31-60, 61-90, 91-180, 181-365, 365+
            total_due = 0.0
            
            for l in lns:
                days = (self.end_date - l.date).days if l.date else 0
                amount = float(l.amount_residual or 0.0)
                total_due += amount
                
                if days <= 30:
                    buckets[0] += amount
                elif days <= 60:
                    buckets[1] += amount
                elif days <= 90:
                    buckets[2] += amount
                elif days <= 180:
                    buckets[3] += amount
                elif days <= 365:
                    buckets[4] += amount
                else:
                    buckets[5] += amount
            
            lines_to_create.append({
                'report_id': self.id,
                'partner_name': partner.name,
                'total_due': total_due,
                'bucket_0_30': buckets[0],
                'bucket_31_60': buckets[1],
                'bucket_61_90': buckets[2],
                'bucket_91_180': buckets[3],
                'bucket_181_365': buckets[4],
                'bucket_365_plus': buckets[5],
            })
        
        self.env['customer.aging.line'].create(lines_to_create)
        
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'customer.aging.report',
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
        sheet = workbook.add_worksheet('Customer Aging')
        
        # Headers
        headers = ['Customer', 'Total Due', '0-30', '31-60', '61-90', '91-180', '181-365', '365+']
        for col, h in enumerate(headers):
            sheet.write(0, col, h)
        
        # Data
        domain = [
            ('date', '<=', self.end_date),
            ('reconciled', '=', False),
            ('parent_state', '=', 'posted'),
            ('account_id.account_type', '=', 'asset_receivable')
        ]
        
        # Add partner filter if customer is selected
        if self.partner_id:
            domain.append(('partner_id', '=', self.partner_id.id))
        
        lines = self.env['account.move.line'].search(domain)
        partners = {}
        for l in lines:
            partner = l.partner_id
            if not partner:
                continue
            partners.setdefault(partner.id, []).append(l)
        
        row = 1
        for pid, lns in partners.items():
            partner = self.env['res.partner'].browse(pid)
            buckets = [0, 0, 0, 0, 0, 0]
            total_due = 0.0
            
            for l in lns:
                days = (self.end_date - l.date).days if l.date else 0
                amount = float(l.amount_residual or 0.0)
                total_due += amount
                
                if days <= 30:
                    buckets[0] += amount
                elif days <= 60:
                    buckets[1] += amount
                elif days <= 90:
                    buckets[2] += amount
                elif days <= 180:
                    buckets[3] += amount
                elif days <= 365:
                    buckets[4] += amount
                else:
                    buckets[5] += amount
            
            sheet.write(row, 0, partner.name)
            sheet.write(row, 1, float(total_due))
            sheet.write(row, 2, float(buckets[0]))
            sheet.write(row, 3, float(buckets[1]))
            sheet.write(row, 4, float(buckets[2]))
            sheet.write(row, 5, float(buckets[3]))
            sheet.write(row, 6, float(buckets[4]))
            sheet.write(row, 7, float(buckets[5]))
            row += 1
        
        workbook.close()
        
        attachment = self.env['ir.attachment'].create({
            'name': f'customer_aging_{self.end_date}.xlsx',
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
        return self.env.ref('all_reports_full.report_customer_aging_pdf').report_action(self)

    def get_report_data(self):
        """Get data for PDF report"""
        domain = [
            ('date', '<=', self.end_date),
            ('reconciled', '=', False),
            ('parent_state', '=', 'posted'),
            ('account_id.account_type', '=', 'asset_receivable')
        ]
        
        # Add partner filter if customer is selected
        if self.partner_id:
            domain.append(('partner_id', '=', self.partner_id.id))
        
        lines = self.env['account.move.line'].search(domain)
        partners_data = {}
        
        for l in lines:
            if not l.partner_id:
                continue
            pid = l.partner_id.id
            if pid not in partners_data:
                partners_data[pid] = {'partner': l.partner_id, 'lines': [], 'buckets': [0,0,0,0,0,0], 'total': 0}
            
            days = (self.end_date - l.date).days if l.date else 0
            amount = float(l.amount_residual or 0.0)
            partners_data[pid]['total'] += amount
            partners_data[pid]['lines'].append(l)
            
            if days <= 30:
                partners_data[pid]['buckets'][0] += amount
            elif days <= 60:
                partners_data[pid]['buckets'][1] += amount
            elif days <= 90:
                partners_data[pid]['buckets'][2] += amount
            elif days <= 180:
                partners_data[pid]['buckets'][3] += amount
            elif days <= 365:
                partners_data[pid]['buckets'][4] += amount
            else:
                partners_data[pid]['buckets'][5] += amount
        
        return list(partners_data.values())


class CustomerAgingLine(models.TransientModel):
    _name = 'customer.aging.line'
    _description = 'Customer Aging Line'

    report_id = fields.Many2one('customer.aging.report', string='Report', ondelete='cascade')
    partner_name = fields.Char(string='Customer')
    total_due = fields.Float(string='Total Due')
    bucket_0_30 = fields.Float(string='0-30 Days')
    bucket_31_60 = fields.Float(string='31-60 Days')
    bucket_61_90 = fields.Float(string='61-90 Days')
    bucket_91_180 = fields.Float(string='91-180 Days')
    bucket_181_365 = fields.Float(string='181-365 Days')
    bucket_365_plus = fields.Float(string='365+ Days')