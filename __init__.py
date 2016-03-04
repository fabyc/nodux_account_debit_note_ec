#This file is part of Tryton.  The COPYRIGHT file at the top level of
#this repository contains the full copyright notices and license terms.
from trytond.pool import Pool
from .invoice import *
from .account import *
def register():
    Pool.register(
        FiscalYear, 
        Period,
        DebitNoteStart,
        Invoice,
        module='nodux_account_debit_note_ec', type_='model')
    Pool.register(
        DebitNote,
        module='nodux_account_debit_note_ec', type_='wizard')
