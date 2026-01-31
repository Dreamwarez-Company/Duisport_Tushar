# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError
import io, base64
from datetime import datetime

try:
    import xlsxwriter
except Exception:
    xlsxwriter = None

class ChartOfAccountsReport(models.TransientModel):
    _name = 'chart.of.accounts.report'
    _description = 'Chart of Accounts Report'

    date_from = fields.Date(string='Start Date', required=True, default=fields.Date.context_today)
    date_to = fields.Date(string='End Date', required=True, default=fields.Date.context_today)
    line_ids = fields.One2many('chart.of.accounts.line', 'report_id', string='Lines')
    show_entries = fields.Boolean(string='Show Journal Entries', default=True)

    def action_view_report(self):
        """Fetch and display report data with entries"""
        self.line_ids.unlink()
        
        accounts = self.env['account.account'].search([], order='code')
        lines_to_create = []
        
        for acc in accounts:
            acc_type = ''
            if hasattr(acc, 'account_type'):
                acc_type = dict(acc._fields['account_type'].selection).get(acc.account_type, acc.account_type or '')
            
            # Get move lines for this account within date range
            domain = [
                ('account_id', '=', acc.id),
                ('date', '>=', self.date_from),
                ('date', '<=', self.date_to),
                ('parent_state', '=', 'posted')  # Only posted entries
            ]
            move_lines = self.env['account.move.line'].search(domain, order='date, id')
            
            # Create main account line
            lines_to_create.append({
                'report_id': self.id,
                'account_code': acc.code or '',
                'account_name': acc.name,
                'account_type': acc_type,
                'reconcile': 'Yes' if acc.reconcile else 'No',
                'is_account': True,
                'entry_count': len(move_lines),
            })
            
            # Create entry lines if show_entries is enabled
            if self.show_entries:
                for line in move_lines:
                    lines_to_create.append({
                        'report_id': self.id,
                        'is_account': False,
                        'entry_date': line.date,
                        'entry_reference': line.move_id.name or '',
                        'entry_label': line.name or '',
                        'entry_partner': line.partner_id.name or '',
                        'entry_debit': line.debit,
                        'entry_credit': line.credit,
                        'entry_balance': line.debit - line.credit,
                    })
        
        self.env['chart.of.accounts.line'].create(lines_to_create)
        
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'chart.of.accounts.report',
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'new',
        }

    def action_download_xlsx(self):
        """Download Excel report with entries"""
        if xlsxwriter is None:
            raise UserError(_('Python library xlsxwriter is required for Excel export.'))
        
        workbook_stream = io.BytesIO()
        workbook = xlsxwriter.Workbook(workbook_stream, {'in_memory': True})
        sheet = workbook.add_worksheet('Chart of Accounts')
        
        # Formats
        header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#D3D3D3',
            'border': 1
        })
        account_format = workbook.add_format({
            'bold': True,
            'bg_color': '#E8E8E8'
        })
        number_format = workbook.add_format({'num_format': '#,##0.00'})
        
        # Report header
        sheet.merge_range('A1:H1', 'Chart of Accounts Report', workbook.add_format({
            'bold': True, 'font_size': 14, 'align': 'center'
        }))
        sheet.write('A2', f'Period: {self.date_from} to {self.date_to}')
        
        # Headers
        row = 3
        headers = ['Account Code', 'Account Name', 'Type', 'Reconcile', 'Date', 'Reference', 'Label', 'Partner', 'Debit', 'Credit', 'Balance']
        for col, h in enumerate(headers):
            sheet.write(row, col, h, header_format)
        
        # Data
        accounts = self.env['account.account'].search([], order='code')
        row = 4
        
        for acc in accounts:
            acc_type = ''
            if hasattr(acc, 'account_type'):
                acc_type = dict(acc._fields['account_type'].selection).get(acc.account_type, acc.account_type or '')
            
            # Account header row
            sheet.write(row, 0, acc.code or '', account_format)
            sheet.write(row, 1, acc.name, account_format)
            sheet.write(row, 2, acc_type, account_format)
            sheet.write(row, 3, 'Yes' if acc.reconcile else 'No', account_format)
            row += 1
            
            # Get move lines
            domain = [
                ('account_id', '=', acc.id),
                ('date', '>=', self.date_from),
                ('date', '<=', self.date_to),
                ('parent_state', '=', 'posted')
            ]
            move_lines = self.env['account.move.line'].search(domain, order='date, id')
            
            if move_lines:
                for line in move_lines:
                    sheet.write(row, 4, line.date.strftime('%Y-%m-%d') if line.date else '')
                    sheet.write(row, 5, line.move_id.name or '')
                    sheet.write(row, 6, line.name or '')
                    sheet.write(row, 7, line.partner_id.name or '')
                    sheet.write(row, 8, line.debit, number_format)
                    sheet.write(row, 9, line.credit, number_format)
                    sheet.write(row, 10, line.debit - line.credit, number_format)
                    row += 1
            else:
                sheet.write(row, 4, 'No entries in this period')
                row += 1
            
            row += 1  # Empty row between accounts

        # Adjust column widths
        sheet.set_column('A:A', 15)
        sheet.set_column('B:B', 30)
        sheet.set_column('C:C', 20)
        sheet.set_column('D:D', 12)
        sheet.set_column('E:E', 12)
        sheet.set_column('F:F', 15)
        sheet.set_column('G:G', 30)
        sheet.set_column('H:H', 25)
        sheet.set_column('I:K', 15)

        workbook.close()
        
        attachment = self.env['ir.attachment'].create({
            'name': f'chart_of_accounts_{self.date_from}_{self.date_to}.xlsx',
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
        return self.env.ref('all_reports_full.report_chart_of_accounts_pdf').report_action(self)


class ChartOfAccountsLine(models.TransientModel):
    _name = 'chart.of.accounts.line'
    _description = 'Chart of Accounts Line'

    report_id = fields.Many2one('chart.of.accounts.report', string='Report', ondelete='cascade')
    
    # Account fields
    is_account = fields.Boolean(string='Is Account', default=False)
    account_code = fields.Char(string='Account Code')
    account_name = fields.Char(string='Account Name')
    account_type = fields.Char(string='Type')
    reconcile = fields.Char(string='Reconcile')
    entry_count = fields.Integer(string='Entry Count')
    
    # Entry fields
    entry_date = fields.Date(string='Date')
    entry_reference = fields.Char(string='Reference')
    entry_label = fields.Char(string='Label')
    entry_partner = fields.Char(string='Partner')
    entry_debit = fields.Float(string='Debit')
    entry_credit = fields.Float(string='Credit')
    entry_balance = fields.Float(string='Balance')