# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class ModifyDocument(Document):
	def validate(self):
		doc = frappe.get_doc(self.document_type, self.document_no)
		if doc.docstatus == 1 and self.change_state_to == "Change to Draft":
			frappe.throw("Not allowed to change to Draft as its already submitted")

		if self.document_type=="Payroll Entry":
			# on payrolle entry, sws contribution from salary slip need to be updated. and Adv deduction from salary structure need to be updated
			# so do not allow changing state of payroll entry
			# frappe.throw("Not allowed to change the state of Payroll Entry document.")
			self.validate_payroll()
		
	def on_submit(self):
		self.change_state()
		self.delete_payroll()

	def change_state(self):
		if self.document_type!="Payroll Entry":
			if self.change_state_to == "Change to Draft":
				if self.document_type=="Travel Authorization":
					frappe.db.sql("update `tabTravel Authorization` set docstatus='0', workflow_state='Draft' where name='{}'".format(self.document_no))
					frappe.db.sql("update `tabTravel Authorization Item` set docstatus='0' where parent='{}'".format(self.document_no))
				elif self.document_type=="Travel Claim":
					frappe.db.sql("update `tabTravel Claim` set docstatus='0', workflow_state='Draft' where name='{}'".format(self.document_no))
					frappe.db.sql("update `tabTravel Claim Item` set docstatus='0' where parent='{}'".format(self.document_no))
		else:
			if self.change_state_to == "Change to Draft":
				frappe.db.sql("""update `tabPayroll Entry` 
							set docstatus=0, successful=0, failed=0, salary_slips_created=0
						where name='{}'""".format(self.document_no))
				frappe.db.commit()

	def validate_payroll(self):
		flag=False
		for b in frappe.db.sql("""select distinct(je.name) as journal_entry
								from `tabJournal Entry` je inner join `tabJournal Entry Account` jea
								on je.name=jea.parent
								where jea.reference_type="Payroll Entry"
								and jea.reference_name="{}"
							""".format(self.document_no), as_dict=True):
			doc = frappe.get_doc("Journal Entry", b.journal_entry)
			if doc.docstatus==1:
				flag = True
		if flag:
			frappe.throw("Not allowed to delete the document as the JEs are submitted")

	def delete_payroll(self):
		if self.document_type=="Payroll Entry" and self.change_state_to == "Delete the Document":
			for b in frappe.db.sql("select name from `tabSalary Slip` where payroll_entry='{}'".format(self.document_no), as_dict=True):
				frappe.db.sql("Delete from `tabSalary Detail` where parent='{}'".format(b.name))
				frappe.db.sql("Delete from `tabOvertime Item` where parent='{}'".format(b.name))
				frappe.db.sql("Delete from `tabSalary Slip Timesheet` where parent='{}'".format(b.name))
				frappe.db.sql("Delete from `tabSalary Slip Item` where parent='{}'".format(b.name))
				frappe.db.sql("Delete from `tabSalary Slip` where name='{}'".format(b.name))
			frappe.db.sql("""update `tabPayroll Entry` 
							set docstatus=0, successful=0, failed=0, salary_slips_created=0
						where name='{}'""".format(self.document_no))
			frappe.db.commit()