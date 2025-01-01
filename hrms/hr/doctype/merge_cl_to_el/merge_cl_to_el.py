# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import msgprint
from frappe.model.document import Document
from frappe.utils import flt, cint, nowdate, getdate, formatdate
from erpnext.accounts.utils import get_fiscal_year
from hrms.hr.doctype.leave_application.leave_application \
        import get_leave_allocation_records, get_leave_balance_on, get_approved_leaves_for_period
from frappe.utils import getdate, get_first_day, get_last_day, flt
from hrms.hr.doctype.leave_ledger_entry.leave_ledger_entry import create_leave_ledger_entry

class MergeCLToEL(Document):
	def validate(self):
		self.validate_duplicate()

	def validate_duplicate(self):
		current_fiscal_year = get_fiscal_year(getdate(nowdate()), company=self.company)[0]
		query = """select name from `tabMerge CL To EL` where docstatus != 2 and fiscal_year = '{0}' and name != '{1}'
			""".format(self.fiscal_year, self.name)
		if self.branch:
			query += " and branch = '{0}'".format(self.branch)
		doc = frappe.db.sql(query)
			
	@frappe.whitelist()		
	def get_data(self):
		fy_start_end_date = frappe.db.get_value("Fiscal Year", self.fiscal_year, ["year_start_date", "year_end_date"])
		if not fy_start_end_date:
			frappe.throw(_("Fiscal Year {0} not found.").format(self.fiscal_year))
	
		from_date = get_first_day(getdate(fy_start_end_date[0]))
		to_date = get_last_day(getdate(fy_start_end_date[1]))
		employee = ''

		filters_dict = { "status": "Active", "company": self.company}
		if self.branch:
			filters_dict['branch'] = self.branch

		active_employees = frappe.get_all("Employee",
			filters = filters_dict,
			fields = ["name", "employee_name", "department", "branch", "date_of_joining"])

		self.set('items', [])
		for employee in active_employees:
			#leaves allocated
			leaves_allocated = 0.0
			allocation = get_leave_allocation_records(employee=employee.name, date=to_date, leave_type=self.leave_type)
			if allocation:
				leaves_allocated = allocation[self.leave_type]['total_leaves_allocated']
				
			# leaves taken
			leaves_taken = get_approved_leaves_for_period(employee.name, self.leave_type,
				from_date, to_date)

			# closing balance
			employee_id = employee.name
			employee_name = employee.employee_name
			leave_balance = flt(leaves_allocated) - flt(leaves_taken)
			if leave_balance > 0:
				row = self.append('items', {})
				d = {'employee': employee_id, 'employee_name': employee_name,\
					'leaves_allocated': leaves_allocated, 'leaves_taken': round(leaves_taken,2), 'leave_balance': round(leave_balance,2)}
				row.update(d)
	
	def create_leave_ledger_entry(self):
		cur_fiscal_year = get_fiscal_year(self.posting_date)
		fiscal_year_start_date = cur_fiscal_year[1]
		fiscal_year_end_date = cur_fiscal_year[2]
		for em in self.items:
			doc = frappe.new_doc("Leave Ledger Entry")
			doc.employee = em.employee
			doc.employee_name = em.employee_name
			doc.from_date = fiscal_year_start_date
			doc.to_date = fiscal_year_end_date
			doc.leave_type = self.merging_to
			doc.transaction_type = self.doctype
			doc.transaction_name = self.name
			doc.leaves = em.leave_balance
			doc.is_carry_forward = 1
			doc.flags.ignore_validate = True
			doc.insert(ignore_permissions=True)
			doc.submit()

	def on_submit(self):
		self.create_leave_ledger_entry()

	def on_cancel(self):
		frappe.db.sql("""DELETE FROM `tabLeave Ledger Entry` WHERE `transaction_name`=%s """,(self.name))

