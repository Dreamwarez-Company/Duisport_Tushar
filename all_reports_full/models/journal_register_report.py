# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError
import io, base64
from datetime import datetime

try:
    import xlsxwriter
except Exception:
    xlsxwriter = None

class JournalRegisterReport(models.TransientModel):
    _name = 'journal.register.report'
    _description = 'Journal Register Report'

    date_from = fields.Date(string='Start Date', required=True, default=fields.Date.context_today)
    date_to = fields.Date(string='End Date', required=True, default=fields.Date.context_today)
    journal_ids = fields.Many2many('account.journal', string='Journals', required=True)
    target_move = fields.Selection([
        ('posted', 'Posted Entries'),
        ('all', 'All Entries')
    ], string='Target Moves', required=True, default='posted')
    line_ids = fields.One2many('journal.register.line', 'report_id', string='Lines')

    def action_view_report(self):
        """Fetch and display journal register data"""
        self.line_ids.unlink()
        
        # Build domain
        domain = [
            ('journal_id', 'in', self.journal_ids.ids),
            ('date', '>=', self.date_from),
            ('date', '<=', self.date_to),
        ]
        
        if self.target_move == 'posted':
            domain.append(('state', '=', 'posted'))
        
        # Get journal entries
        journal_entries = self.env['account.move'].search(domain, order='date, name')
        
        lines_to_create = []
        
        for move in journal_entries:
            # Create journal entry header
            lines_to_create.append({
                'report_id': self.id,
                'is_header': True,
                'move_id': move.id,
                'move_name': move.name or '',
                'move_date': move.date,
                'journal_id': move.journal_id.id,
                'journal_name': move.journal_id.name,
                'partner_id': move.partner_id.id if move.partner_id else False,
                'partner_name': move.partner_id.name if move.partner_id else '',
                'reference': move.ref or '',
                'state': dict(move._fields['state'].selection).get(move.state, move.state),
            })
            
            # Create lines for each move line
            for line in move.line_ids:
                lines_to_create.append({
                    'report_id': self.id,
                    'is_header': False,
                    'move_id': move.id,
                    'account_code': line.account_id.code or '',
                    'account_name': line.account_id.name or '',
                    'line_name': line.name or '',
                    'line_partner': line.partner_id.name if line.partner_id else '',
                    'debit': line.debit,
                    'credit': line.credit,
                    'balance': line.debit - line.credit,
                })
        
        self.env['journal.register.line'].create(lines_to_create)
        
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'journal.register.report',
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
        sheet = workbook.add_worksheet('Journal Register')
        
        # Formats
        title_format = workbook.add_format({
            'bold': True,
            'font_size': 14,
            'align': 'center',
            'valign': 'vcenter'
        })
        header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#D3D3D3',
            'border': 1,
            'align': 'center'
        })
        move_header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#E8E8E8',
            'border': 1
        })
        number_format = workbook.add_format({'num_format': '#,##0.00'})
        date_format = workbook.add_format({'num_format': 'yyyy-mm-dd'})
        
        # Report title
        sheet.merge_range('A1:I1', 'Journal Register Report', title_format)
        sheet.write('A2', f'Period: {self.date_from} to {self.date_to}')
        journal_names = ', '.join(self.journal_ids.mapped('name'))
        sheet.write('A3', f'Journals: {journal_names}')
        
        # Column headers
        row = 4
        headers = ['Date', 'Journal Entry', 'Journal', 'Partner', 'Reference', 'Account', 'Label', 'Debit', 'Credit', 'Balance']
        for col, header in enumerate(headers):
            sheet.write(row, col, header, header_format)
        
        # Build domain
        domain = [
            ('journal_id', 'in', self.journal_ids.ids),
            ('date', '>=', self.date_from),
            ('date', '<=', self.date_to),
        ]
        
        if self.target_move == 'posted':
            domain.append(('state', '=', 'posted'))
        
        # Get journal entries
        journal_entries = self.env['account.move'].search(domain, order='date, name')
        
        row = 5
        total_debit = 0
        total_credit = 0
        
        for move in journal_entries:
            # Move header row
            sheet.write(row, 0, move.date, date_format)
            sheet.write(row, 1, move.name or '', move_header_format)
            sheet.write(row, 2, move.journal_id.name, move_header_format)
            sheet.write(row, 3, move.partner_id.name if move.partner_id else '', move_header_format)
            sheet.write(row, 4, move.ref or '', move_header_format)
            sheet.write(row, 5, dict(move._fields['state'].selection).get(move.state, move.state), move_header_format)
            row += 1
            
            # Move lines
            for line in move.line_ids:
                sheet.write(row, 5, f"{line.account_id.code or ''} - {line.account_id.name or ''}")
                sheet.write(row, 6, line.name or '')
                sheet.write(row, 7, line.debit, number_format)
                sheet.write(row, 8, line.credit, number_format)
                sheet.write(row, 9, line.debit - line.credit, number_format)
                
                total_debit += line.debit
                total_credit += line.credit
                row += 1
            
            # Blank row between entries
            row += 1
        
        # Grand totals
        sheet.write(row, 6, 'Grand Total:', move_header_format)
        sheet.write(row, 7, total_debit, number_format)
        sheet.write(row, 8, total_credit, number_format)
        sheet.write(row, 9, total_debit - total_credit, number_format)
        
        # Adjust column widths
        sheet.set_column('A:A', 12)
        sheet.set_column('B:B', 18)
        sheet.set_column('C:C', 20)
        sheet.set_column('D:D', 25)
        sheet.set_column('E:E', 20)
        sheet.set_column('F:F', 35)
        sheet.set_column('G:G', 35)
        sheet.set_column('H:J', 15)

        workbook.close()
        
        attachment = self.env['ir.attachment'].create({
            'name': f'journal_register_{self.date_from}_{self.date_to}.xlsx',
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
        return self.env.ref('all_reports_full.report_journal_register_pdf').report_action(self)


class JournalRegisterLine(models.TransientModel):
    _name = 'journal.register.line'
    _description = 'Journal Register Line'

    report_id = fields.Many2one('journal.register.report', string='Report', ondelete='cascade')
    
    # Header fields (for journal entry header)
    is_header = fields.Boolean(string='Is Header', default=False)
    move_id = fields.Many2one('account.move', string='Journal Entry')
    move_name = fields.Char(string='Entry Number')
    move_date = fields.Date(string='Date')
    journal_id = fields.Many2one('account.journal', string='Journal')
    journal_name = fields.Char(string='Journal Name')
    partner_id = fields.Many2one('res.partner', string='Partner')
    partner_name = fields.Char(string='Partner Name')
    reference = fields.Char(string='Reference')
    state = fields.Char(string='Status')
    
    # Line fields (for journal entry lines)
    account_code = fields.Char(string='Account Code')
    account_name = fields.Char(string='Account Name')
    line_name = fields.Char(string='Label')
    line_partner = fields.Char(string='Partner')
    debit = fields.Float(string='Debit', digits=(16, 2))
    credit = fields.Float(string='Credit', digits=(16, 2))
    balance = fields.Float(string='Balance', digits=(16, 2))