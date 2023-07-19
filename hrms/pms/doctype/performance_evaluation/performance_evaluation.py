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
		month_start_date = "-".join([str(self.fiscal_year), self.month, "01"])
		month_end_date = "-".join([str(self.fiscal_year), self.month, "10"])
		self.start_date = getdate(month_start_date)
		self.end_date = getdate(month_end_date)

	def validate(self):
		self.set_evaluation_period_dates()
		self.check_duplicate_entry()
	
	def check_duplicate_entry(self):
		if frappe.db.exists("Performance Evaluation", {'employee': self.employee, 'fiscal_year': self.fiscal_year, 'docstatus': 1}):
			frappe.throw(_('You have already set Performance evaluation <b>{}</b>'.format(self.fiscal_year)))

	@frappe.whitelist()
	def get_competency(self):

		# fetch employee category based on employee designation
		# employee_category = frappe.db.sql("""
		# 	select ec.employee_category 
		# 	from `tabEmployee Category` ec 
		# 	inner join `tabEmployee Category Group` ecg
		# 	on ec.name = ecg.parent
		# 	where ecg.designation = '{}'
		# """.format(self.designation), as_dict=True)

		# if not employee_category:
		# 	frappe.throw(
		# 		_('Your designation <b>{0}</b> is not defined in the Employee Category. Contact your HR for necessary changes'.format(self.designation)))

		data = frappe.db.sql("""
			select wc.competency, wc.weightage, wc.rating_4, wc.rating_3, wc.rating_2, wc.rating_1
			from `tabWork Competency` wc
			inner join `tabWork Competency Item` wci
			on wc.name = wci.parent
			where wci.applicable = 1
			and wci.employee_group = '{}'
			order by wc.competency
		""".format(self.employee_group), as_dict=True)

		if not data:
			frappe.throw(_('There is no Work Competency defined'))
		
		self.set('work_competency', [])
		for d in data:
			row = self.append('work_competency', {})
			row.update(d)

	@frappe.whitelist()
	def get_evaluators(self):
		if (frappe.db.get_value('Employee', self.employee, 'eval_1')):
			self.evaluator_1 = frappe.db.get_value('Employee', self.employee, 'eval_1')
			self.eval_1_name = frappe.db.get_value('Employee', self.evaluator_1, 'employee_name')
			self.eval_1_user_id = frappe.db.get_value('Employee', self.evaluator_1, 'user_id')
		else: 
			frappe.throw('Set Evaluator 1 for employee ID {}'.format(self.employee))

		if (frappe.db.get_value('Employee', self.employee, 'eval_2')):
			self.evaluator_2 = frappe.db.get_value('Employee', self.employee, 'eval_2')
			self.eval_2_name = frappe.db.get_value('Employee', self.evaluator_2, 'employee_name')
			self.eval_2_user_id = frappe.db.get_value('Employee', self.evaluator_2, 'user_id')
		else: 
			frappe.throw('Set Evaluator 2 for employee ID {}'.format(self.employee))

		if self.employee_group != 'Administration & Support':
			if (frappe.db.get_value('Employee', self.employee, 'eval_3')):
				self.evaluator_3 = frappe.db.get_value('Employee', self.employee, 'eval_3')
				self.eval_3_name = frappe.db.get_value('Employee', self.evaluator_3, 'employee_name')
				self.eval_3_user_id = frappe.db.get_value('Employee', self.evaluator_3, 'user_id')
			else: 
				frappe.throw('Set Evaluator 3 for employee ID {}'.format(self.employee))