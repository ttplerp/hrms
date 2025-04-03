# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

from frappe import _
from frappe.utils import flt
from erpnext.accounts.doctype.accounts_settings.accounts_settings import get_bank_account

class BulkPayment(Document):
	def validate(self):
		pass

	def on_submit(self):
		self.post_journal_entry()

	def on_cancel(self):
		self.ignore_linked_doctypes = ("GL Entry", "Payment Ledger Entry")

	def make_filters(self):
		filters = frappe._dict(
			from_date = self.from_date,
			to_date	= self.to_date,
			company = self.company,
			bulk_payment = self.name
		)
		return filters
	
	def post_journal_entry(self):
		default_bank_account = frappe.db.get_value("Company", self.company, "default_bank_account")
		if not default_bank_account:
			frappe.throw("Setup Default Expense Bank Account for your Company")

		expense_account = frappe.db.get_value("Company", self.company, "leave_encashment_account")
		if not expense_account:
			frappe.throw("Setup Leave Encashment Account in HR Accounts Settings")

		tax_account = frappe.db.get_value("Company", self.company, "salary_tax_account")
		if not tax_account:
			frappe.throw("Setup Tax Account in HR Accounts Settings")
		
		default_payable_account = frappe.db.get_value("Company", self.company, "salary_payable_account")
		company_cc              = frappe.db.get_value("Company", self.company, "company_cost_center")

		cc = {}
		tax_amount = net_amount = 0 
		for d in self.items:
			tax_amount += d.tax_amount
			net_amount += d.net_amount
			if d.cost_center not in cc:
				cc.update({
					d.cost_center: {
			   			"total_amount": d.total_amount,
			   			"tax_amount": d.tax_amount,
			   			"net_amount": d.net_amount,
					}
		   		})
			else:
				cc[d.cost_center]['total_amount'] += flt(d.total_amount)
				cc[d.cost_center]['tax_amount'] += flt(d.tax_amount)
				cc[d.cost_center]['net_amount'] += flt(d.net_amount)
		
		#Payables Journal Entry -----------------------------------------------
		payables_je = frappe.new_doc("Journal Entry")
		payables_je.voucher_type= "Journal Entry"
		payables_je.naming_series = "Journal Voucher"
		payables_je.title = "Leave Encashment "+str(self.posting_date)+" - To Payables"
		payables_je.remark =  "Leave Encashment "+str(self.posting_date)+" - To Payables"
		payables_je.posting_date = self.posting_date               
		payables_je.company = self.company
		payables_je.branch = self.branch
		
		for rec in cc:
			payables_je.append("accounts", {
					"account": expense_account,
					"reference_type": self.doctype,
					"reference_name": self.name,
					"cost_center": rec,
					"debit_in_account_currency": flt(cc[rec]['total_amount']),
					"debit": flt(cc[rec]['total_amount']),
				})
		
		#Salary Tax
		if tax_amount > 0:
			payables_je.append("accounts", {
					"account": tax_account,
					"reference_type": self.doctype,
					"reference_name": self.name,
					"cost_center": company_cc,
					"credit_in_account_currency": flt(tax_amount),
					"party_check": 0,
					"credit": flt(tax_amount),
				})
		#Salary Payble
		payables_je.append("accounts", {
				"account": default_payable_account,
				"reference_type": self.doctype,
				"reference_name": self.name,
				"cost_center": company_cc,
				"credit_in_account_currency": flt(net_amount),
				"credit": flt(net_amount),
				"party_check": 0
			})

		payables_je.flags.ignore_permissions = 1
		payables_je.insert()
		payables_je.submit()
		
		#Payables JE End -----------------------------------------------------
		sthc_je = frappe.new_doc("Journal Entry")
		sthc_je.voucher_type= "Bank Entry"
		sthc_je.naming_series = "Bank Payment Voucher"
		sthc_je.title = "Leave Encashment Tax for "+ self.posting_date
		sthc_je.remark =  "Leave Encashment Tax for "+self.posting_date
		sthc_je.posting_date = self.posting_date            
		sthc_je.company = self.company
		sthc_je.branch = self.branch
		
		#Salary Tax
		if tax_amount > 0:
			sthc_je.append("accounts", {
					"account": frappe.db.get_value("Salary Component", "Salary Tax", "gl_head"),
					"reference_type": self.doctype,
					"reference_name": self.name,
					"cost_center": company_cc,
					"debit_in_account_currency": flt(tax_amount),
					"debit": flt(tax_amount),
					"party_check": 0
				})
		#To Bank Account
		sthc_je.append("accounts", {
				"account": default_bank_account,
				"reference_type": self.doctype,
				"reference_name": self.name,
				"cost_center": company_cc,
				"credit_in_account_currency": flt(tax_amount),
				"credit": flt(tax_amount),
			})

		sthc_je.flags.ignore_permissions = 1 
		sthc_je.insert()

		#Payables to Bank Entry -----------------------------------------------
		pb_je = frappe.new_doc("Journal Entry")
		pb_je.voucher_type= "Bank Entry"
		pb_je.naming_series = "Bank Payment Voucher"
		pb_je.title = "Leave Encashment for the fiscal year of "+self.posting_date
		pb_je.remark = "Leave Encashment for the fiscal year of "+self.posting_date
		pb_je.posting_date = self.posting_date
		pb_je.company = self.company
		pb_je.branch = self.branch
		
		#Salary Payable
		pb_je.append("accounts", {
				"account": default_payable_account,
				"reference_type": self.doctype,
				"reference_name": self.name,
				"cost_center": company_cc,
				"debit_in_account_currency": flt(net_amount),
				"debit": flt(net_amount),
				"party_check": 0
			})
		#To Bank Account
		pb_je.append("accounts", {
				"account": default_bank_account,
				"reference_type": self.doctype,
				"reference_name": self.name,
				"cost_center": company_cc,
				"credit_in_account_currency": flt(net_amount),
				"credit": flt(net_amount),
			})

		pb_je.flags.ignore_permissions = 1 
		pb_je.insert()
		frappe.db.commit()

	@frappe.whitelist()
	def fill_reference_details(self):
		filters = self.make_filters()
		data = get_transaction_list(filters=filters, as_dict=True)

		self.set("items", [])

		if not data:
			error_msg = _(
				"No transactions found for the mentioned criteria:<br>From Date: {0}"
			).format(
				frappe.bold(self.from_date),
			)
			if self.to_date:
				error_msg += "<br>" + _("To Date: {0}").format(frappe.bold(self.to_date))
			frappe.throw(error_msg, title=_("No transactions found"))

		self.set("items", data)

def get_transaction_list(filters, as_dict=True) -> list:
    return frappe.db.sql("""
        SELECT 
            'Leave Encashment' as reference_type,
            t1.name as reference_name,
            t1.employee,
            t1.employee_name,
            t1.encashment_amount as total_amount,
            t1.encashment_tax as tax_amount,
            t1.payable_amount as net_amount,
			t2.cost_center
        FROM `tabLeave Encashment` t1, `tabEmployee` t2
        WHERE t1.employee = t2.name
			AND t1.docstatus = 1
            AND t1.company = %(company)s
            AND t1.encashment_date BETWEEN %(from_date)s AND %(to_date)s
            AND NOT EXISTS (
                SELECT 1
                FROM `tabBulk Payment Item` bpi
                JOIN `tabBulk Payment` bp ON bp.name = bpi.parent
                WHERE bpi.reference_name = t1.name
                    AND bpi.parent != %(bulk_payment)s
                    AND bp.docstatus != 2
            )
    """, filters, as_dict=as_dict)