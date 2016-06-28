#This file is part of Tryton.  The COPYRIGHT file at the top level of
#this repository contains the full copyright notices and license terms.

from trytond.model import ModelView, fields
from trytond.pool import PoolMeta, Pool
from trytond.pyson import If, Eval, Bool, Id
from trytond.wizard import Wizard, StateTransition, StateView, Button
from trytond.transaction import Transaction
from trytond.modules.company import CompanyReport
from trytond.wizard import Wizard, StateView, StateTransition, StateAction, \
    Button
from decimal import Decimal

conversor = None
try:
    from numword import numword_es
    conversor = numword_es.NumWordES()
except:
    print("Warning: Does not possible import numword module!")
    print("Please install it...!")

__all__ = ['Invoice','DebitNoteStart','DebitNote']

_STATES = {
    'readonly': Eval('state') != 'draft',
}
_DEPENDS = ['state']

_TYPE = [
    ('out_debit_note','Nota de Debito Cliente'),
]

_TYPE2JOURNAL = {
    'out_withholding': 'revenue',
    'in_withholding': 'expense',
    'anticipo':'revenue',
    'out_invoice': 'revenue',
    'in_invoice': 'expense',
    'out_credit_note': 'revenue',
    'in_credit_note': 'expense',
    'out_debit_note': 'revenue',
}

_ZERO = Decimal('0.0')


_DEBIT_TYPE = {
    'out_invoice': 'out_debit_note',
    }

class Invoice:
    __metaclass__ = PoolMeta
    __name__ = 'account.invoice'

    @classmethod
    def __setup__(cls):
        super(Invoice, cls).__setup__()
        cls.state_string = super(Invoice, cls).state.translated('state')
        new_sel = [
            ('out_debit_note', 'Nota de Debito Cliente')
        ]
        if new_sel not in cls.type.selection:
            cls.type.selection.extend(new_sel)

    @fields.depends('type', 'party', 'company')
    def on_change_type(self):
        Journal = Pool().get('account.journal')
        res = {}
        journals = Journal.search([
                ('type', '=', _TYPE2JOURNAL.get(self.type or 'out_debit_note',
                        'revenue')),
                ], limit=1)
        if journals:
            journal, = journals
            res['journal'] = journal.id
            res['journal.rec_name'] = journal.rec_name
        res.update(self.__get_account_payment_term())
        return res

    def _debit(self):
        '''
        Return values to credit invoice.
        '''
        res = {}
        res['type'] = _DEBIT_TYPE[self.type]
        res['number_w'] = self.number
        res['ambiente'] = self.invoice_date
        for field in ('description', 'comment'):
            res[field] = getattr(self, field)

        for field in ('company', 'party', 'invoice_address', 'currency',
                'journal', 'account', 'payment_term'):
            res[field] = getattr(self, field).id


        res['taxes'] = []
        to_create = [tax._credit() for tax in self.taxes if tax.manual]
        if to_create:
            res['taxes'].append(('create', to_create))
        return res

    @classmethod
    def debit(cls, invoices, refund=False):
        '''
        Credit invoices and return ids of new invoices.
        Return the list of new invoice
        '''
        MoveLine = Pool().get('account.move.line')

        new_invoices = []
        for invoice in invoices:
            new_invoice, = cls.create([invoice._debit()])
            new_invoices.append(new_invoice)
            if refund:
                cls.post([new_invoice])
                if new_invoice.state == 'posted':
                    MoveLine.reconcile([l for l in invoice.lines_to_pay
                            if not l.reconciliation] +
                        [l for l in new_invoice.lines_to_pay
                            if not l.reconciliation])
        cls.update_taxes(new_invoices)
        return new_invoices

class DebitNoteStart(ModelView):
    'Debit Note'
    __name__ = 'nodux_account_debit_note_ec.debit_note.start'

class DebitNote(Wizard):
    'Debit Note'
    __name__ = 'nodux_account_debit_note_ec.debit_note'
    #crear referencias:
    start = StateView('nodux_account_debit_note_ec.debit_note.start',
        'nodux_account_debit_note_ec.debit_note_start_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Debit', 'debit', 'tryton-ok', default=True),
            ])
    debit = StateAction('account_invoice.act_invoice_form')

    @classmethod
    def __setup__(cls):
        super(DebitNote, cls).__setup__()

    def do_debit(self, action):
        pool = Pool()
        Invoice = pool.get('account.invoice')

        invoices = Invoice.browse(Transaction().context['active_ids'])

        debit_notes = Invoice.debit(invoices)

        data = {'res_id': [i.id for i in debit_notes]}
        if len(debit_notes) == 1:
            action['views'].reverse()

        return action, data
