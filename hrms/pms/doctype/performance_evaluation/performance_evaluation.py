# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import flt, getdate
from frappe.model.document import Document

class PerformanceEvaluation(Document):
	@frappe.whitelist()
	def set_evaluation_period_dates(self):
		month = int(self.month) + 1
		if month > 12:
			month = 1
		month_start_date = "-".join([str(self.fiscal_year), str(month), "01"])
		month_end_date = "-".join([str(self.fiscal_year), str(month), "10"])
		self.start_date = getdate(month_start_date)
		self.end_date = getdate(month_end_date)

	def validate(self):
		if not self.get("__islocal"):
			self.validate_evaluator_score()
		self.set_evaluation_period_dates()
		self.check_duplicate_entry()

	def on_submit(self):
		self.is_evaluated()
		
	def is_evaluated(self):
		if self.evaluator_score == 0:
			frappe.throw('Evaluator has not evaluated')

	def validate_evaluator_score(self):
		for a in self.work_competency:
			if not a.evaluator:
				a.evaluator = 0
			if a.evaluator < 1 or a.evaluator > a.weightage:
				frappe.throw('Your rating should be in range from <b>1</b> to <b>{}</b>'.format(a.weightage))
			if a.evaluator == 1 or a.evaluator == 4:
				if not a.comment:
					frappe.throw('Write comments for competency <b>{}</b> in row no <b>{}</b>.'.format(a.competency, a.idx))

	
	def check_duplicate_entry(self):
		if frappe.db.exists("Performance Evaluation", {'employee': self.employee, 'fiscal_year': self.fiscal_year, 'month':self.month, 'evaluator': self.evaluator, 'docstatus': 1}):
			frappe.throw(_('You have already evaluated for employee {} for month <b>{}</b> <b>{}</b>'.format(self.month_name, self.fiscal_year)))	

@frappe.whitelist()
def get_permission_query_conditions(user):
	if not user: user = frappe.session.user
	user_roles = frappe.get_roles(user)

	if user == "Administrator":
		return
	# if "HR User" in user_roles:
	# 	return

	return """(
		`tabPerformance Evaluation`.owner = '{user}'
		or
		(`tabPerformance Evaluation`.evaluator_user_id = '{user}' and `tabPerformance Evaluation`.docstatus = 0)
	)""".format(user=user)