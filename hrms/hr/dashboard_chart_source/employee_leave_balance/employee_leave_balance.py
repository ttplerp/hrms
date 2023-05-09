# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


from dateutil.relativedelta import relativedelta

import frappe
from frappe import _
from frappe.utils import getdate
from frappe.utils.dashboard import cache_source


@frappe.whitelist()
@cache_source
def get_data(
	chart_name=None,
	chart=None,
	no_cache=None,
	filters=None,
	from_date=None,
	to_date=None,
	timespan=None,
	time_interval=None,
	heatmap_year=None,
) -> dict[str, list]:
	# if filters:
	# 	filters = frappe.parse_json(filters)
	employee = frappe.db.get_value("Employee", {"user_id":frappe.session.user},"name")
	cond = ''
	if employee:
		cond += ' and employee = {} '.format(employee)
	leave_balace = frappe.db.sql('''select sum(leaves) as leave_count, leave_type from `tabLeave Ledger Entry` where docstatus = 1 group by leave_type'''.format(cond), as_dict=True)
	labels , values = [], []
	for l in leave_balace:
		labels.append(f'{l.leave_type}')
		values.append(l.leave_count)
	return {
		"labels": labels,
		"datasets": [
			{"name": _("Leave Balance"), "values": values},
		],
	}

