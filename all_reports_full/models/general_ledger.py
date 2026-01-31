# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError
import io, base64
from datetime import date

try:
    import xlsxwriter
except Exception:
    xlsxwriter = None

class GeneralLedgerReport(models.TransientModel):
    _name = 'general.ledger.report'
    _description = 'General Ledger Report'

    start_date = fields.Date(string='Start Date', required=True)
    end_date = fields.Date(string='End Date', required=True)
    line_ids = fields.One2many('general.ledger.line', 'report_id', string='Lines')

    def action_view_report(self):
        """Fetch and display report data"""
        self.line_ids.unlink()
        
        domain = [
            ('date', '>=', self.start_date),
            ('date', '<=', self.end_date),
            ('parent_state', '=', 'posted')
        ]
        amls = self.env['account.move.line'].search(domain, order='date,account_id,partner_id')
        
        balance_map = {}
        lines_to_create = []
        
        for line in amls:
            acc = line.account_id
            key = acc.id
            bal = balance_map.get(key, 0.0) + (line.debit - line.credit)
            balance_map[key] = bal
            
            lines_to_create.append({
                'report_id': self.id,
                'date': line.date,
                'journal': line.move_id.journal_id.name or '',
                'account_code': acc.code or '',
                'account_name': acc.name,
                'partner': line.partner_id.name or '',
                'label': line.name or '',
                'debit': line.debit,
                'credit': line.credit,
                'balance': bal,
            })
        
        self.env['general.ledger.line'].create(lines_to_create)
        
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'general.ledger.report',
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
        sheet = workbook.add_worksheet('General Ledger')

        # Headers
        headers = ['Date', 'Journal', 'Account Code', 'Account Name', 'Partner', 'Label', 'Debit', 'Credit', 'Balance']
        for col, h in enumerate(headers):
            sheet.write(0, col, h)

        # Data
        domain = [
            ('date', '>=', self.start_date),
            ('date', '<=', self.end_date),
            ('parent_state', '=', 'posted')
        ]
        amls = self.env['account.move.line'].search(domain, order='date,account_id,partner_id')
        
        balance_map = {}
        row = 1
        for line in amls:
            acc = line.account_id
            key = acc.id
            bal = balance_map.get(key, 0.0) + (line.debit - line.credit)
            balance_map[key] = bal
            
            sheet.write(row, 0, str(line.date))
            sheet.write(row, 1, line.move_id.journal_id.name or '')
            sheet.write(row, 2, acc.code or '')
            sheet.write(row, 3, acc.name)
            sheet.write(row, 4, line.partner_id.name or '')
            sheet.write(row, 5, line.name or '')
            sheet.write(row, 6, float(line.debit))
            sheet.write(row, 7, float(line.credit))
            sheet.write(row, 8, float(bal))
            row += 1

        workbook.close()
        
        attachment = self.env['ir.attachment'].create({
            'name': f'general_ledger_{self.start_date}_{self.end_date}.xlsx',
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
        return self.env.ref('all_reports_full.report_general_ledger_pdf').report_action(self)

    def get_report_data(self):
        """Get data for PDF report"""
        domain = [
            ('date', '>=', self.start_date),
            ('date', '<=', self.end_date),
            ('parent_state', '=', 'posted')
        ]
        return self.env['account.move.line'].search(domain, order='date,account_id')


class GeneralLedgerLine(models.TransientModel):
    _name = 'general.ledger.line'
    _description = 'General Ledger Line'

    report_id = fields.Many2one('general.ledger.report', string='Report', ondelete='cascade')
    date = fields.Date(string='Date')
    journal = fields.Char(string='Journal')
    account_code = fields.Char(string='Account Code')
    account_name = fields.Char(string='Account Name')
    partner = fields.Char(string='Partner')
    label = fields.Char(string='Label')
    debit = fields.Float(string='Debit')
    credit = fields.Float(string='Credit')
    balance = fields.Float(string='Balance')