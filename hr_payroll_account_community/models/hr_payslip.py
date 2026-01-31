# -*- coding: utf-8 -*-
#############################################################################
#    A part of Open HRMS Project <https://www.openhrms.com>
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2023-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author: Cybrosys Techno Solutions(<https://www.cybrosys.com>)
#
#    You can modify it under the terms of the GNU LESSER
#    GENERAL PUBLIC LICENSE (LGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU LESSER GENERAL PUBLIC LICENSE (LGPL v3) for more details.
#
#    You should have received a copy of the GNU LESSER GENERAL PUBLIC LICENSE
#    (LGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
#############################################################################
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class HrPayslip(models.Model):
    """ Extends the standard 'hr.payslip' model to include additional fields
        for accounting purposes."""
    _inherit = 'hr.payslip'

    date = fields.Date(string='Date Account',
                       help="Keep empty to use the period of the "
                            "validation(Payslip) date.")
    journal_id = fields.Many2one('account.journal',
                                 string='Salary Journal',
                                 required=True,
                                 help="Select Salary Journal",
                                 default=lambda self: self.env[
                                     'account.journal'].search(
                                     [('type', '=', 'general')],
                                     limit=1))
    move_id = fields.Many2one('account.move',
                              string='Accounting Entry',
                              readonly=True, copy=False,
                              help="Accounting entry associated with "
                                   "this record")

    @api.model
    def create(self, vals):
        """Create a new payroll slip.This method is called when creating a
            new payroll slip.It checks if 'journal_id' is present in the
            context and, if so, sets the 'journal_id' field in the values."""
        if 'journal_id' in self.env.context:
            vals['journal_id'] = self.env.context.get('journal_id')
        return super(HrPayslip, self).create(vals)

    @api.onchange('contract_id')
    def onchange_contract_id(self):
        """Odoo 17 compatible onchange.
        Sets the salary journal from the contract if available,
        otherwise falls back to default journal.
        """
        for slip in self:
            if slip.contract_id and slip.contract_id.journal_id:
                slip.journal_id = slip.contract_id.journal_id
            else:
                slip.journal_id = self.env['account.journal'].search(
                    [('type', '=', 'general')],
                    limit=1
                )

    def action_payslip_cancel(self):
        """Cancel the payroll slip and its accounting entries (Odoo 17 compatible)."""
        moves = self.mapped('move_id')

        # Cancel posted journal entries safely (Odoo 17)
        posted_moves = moves.filtered(lambda m: m.state == 'posted')
        if posted_moves:
            posted_moves.action_cancel()

        # Remove draft/cancelled moves
        moves.unlink()

        return super(HrPayslip, self).action_payslip_cancel()

    def action_payslip_done(self):
        res = super(HrPayslip, self).action_payslip_done()

        for slip in self:
            line_ids = []
            debit_sum = 0.0
            credit_sum = 0.0

            move_dict = {
                'narration': _('Payslip of %s') % slip.employee_id.name,
                'ref': slip.number,
                'journal_id': slip.journal_id.id,
                'date': slip.date or slip.date_to,
                'move_type': 'entry',
                'company_id': slip.company_id.id,
            }

            for line in slip.line_ids.filtered(lambda l: l.salary_rule_id):
                amount = slip.company_id.currency_id.round(
                    slip.credit_note and -line.total or line.total
                )
                if slip.company_id.currency_id.is_zero(amount):
                    continue

                rule = line.salary_rule_id
                debit_account_id = rule.account_debit_id.id
                credit_account_id = rule.account_credit_id.id

                if debit_account_id:
                    debit = max(amount, 0.0)
                    credit = max(-amount, 0.0)
                    line_ids.append((0, 0, {
                        'name': line.name,
                        'partner_id': line._get_partner_id(credit_account=False),
                        'account_id': debit_account_id,
                        'debit': debit,
                        'credit': credit,
                        'tax_line_id': rule.account_tax_id.id,
                    }))
                    debit_sum += debit - credit

                if credit_account_id:
                    debit = max(-amount, 0.0)
                    credit = max(amount, 0.0)
                    line_ids.append((0, 0, {
                        'name': line.name,
                        'partner_id': line._get_partner_id(credit_account=True),
                        'account_id': credit_account_id,
                        'debit': debit,
                        'credit': credit,
                        'tax_line_id': rule.account_tax_id.id,
                    }))
                    credit_sum += credit - debit

            # Adjustment entries
            if slip.company_id.currency_id.compare_amounts(credit_sum, debit_sum) == -1:
                acc_id = slip.journal_id.default_account_id.id
                if not acc_id:
                    raise UserError(
                        _('The Expense Journal "%s" has not properly configured the Credit Account!')
                        % slip.journal_id.name
                    )
                line_ids.append((0, 0, {
                    'name': _('Adjustment Entry'),
                    'account_id': acc_id,
                    'credit': slip.company_id.currency_id.round(debit_sum - credit_sum),
                }))

            elif slip.company_id.currency_id.compare_amounts(debit_sum, credit_sum) == -1:
                acc_id = slip.journal_id.default_account_id.id
                if not acc_id:
                    raise UserError(
                        _('The Expense Journal "%s" has not properly configured the Debit Account!')
                        % slip.journal_id.name
                    )
                line_ids.append((0, 0, {
                    'name': _('Adjustment Entry'),
                    'account_id': acc_id,
                    'debit': slip.company_id.currency_id.round(credit_sum - debit_sum),
                }))

            move_dict['line_ids'] = line_ids
            move = self.env['account.move'].create(move_dict)

            if not move.line_ids:
                raise UserError(
                    _("You must configure Debit/Credit accounts on at least one Salary Rule.")
                )

            slip.write({'move_id': move.id, 'date': slip.date or slip.date_to})
            move.with_company(slip.company_id).action_post()

        return res
