from odoo import api, fields, models


class AdvanceVendorReportWizard(models.TransientModel):
    _name = "advance.vendor.report.wizard"
    _description = "Advance to Vendors Report Wizard"

    date_from = fields.Date(required=True)
    date_to = fields.Date(required=True)

    # -----------------------------
    # PDF Action
    # -----------------------------
    def action_print_pdf(self):
        return self.env.ref(
            "all_reports_full.action_advance_vendor_report_pdf"
        ).report_action(self)

    # -----------------------------
    # XLSX Action (if needed later)
    # -----------------------------
    # def action_print_xlsx(self):
    #     return self.env.ref(
    #         "all_reports_full.action_advance_vendor_report_xlsx"
    #     ).report_action(self)

    # -----------------------------
    # DATA EXTRACTOR
    # -----------------------------
    def get_report_data(self):
        AccountMoveLine = self.env['account.move.line']

        moves = AccountMoveLine.search([
            ('account_id.account_type', '=', 'payable'),
            ('date', '>=', self.date_from),
            ('date', '<=', self.date_to),
            ('balance', '<', 0),             # advance → negative balance
        ])

        vendors = {}

        for line in moves:
            vendor = line.partner_id

            if vendor.id not in vendors:
                vendors[vendor.id] = {
                    'vendor_name': vendor.name,
                    'entries': [],
                    'total_advance': 0,
                }

            vendors[vendor.id]['entries'].append({
                'date': line.date,
                'journal': line.journal_id.name,
                'ref': line.move_id.name,
                'amount': abs(line.balance),
            })

            vendors[vendor.id]['total_advance'] += abs(line.balance)

        return list(vendors.values())
