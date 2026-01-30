# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe


def execute(filters=None):
	columns = get_columns(filters)
	data = get_data(filters)
	return columns, data

def get_data(filters):
	conditions = []
	if filters.get("from_date"):
		conditions.append("i.posting_date >= %(from_date)s")
	if filters.get("to_date"):
		conditions.append("i.posting_date <= %(to_date)s")
	if filters.get("customer_tpn"):
		conditions.append("i.tpn = %(customer_tpn)s")
	if filters.get("response_status"):
		conditions.append("i.cbs_response = %(response_status)s")
	if filters.get("service_type"):
		conditions.append("d.service_type = %(service_type)s")

	condition_sql = " AND ".join(conditions)
	if condition_sql:
		condition_sql = " AND " + condition_sql

	query = f"""
		SELECT
			i.posting_date invoice_date,
			i.name invoice_number,
			i.tpn customer_tpn,
			i.customer_name customer,
			i.cid customer_id,
			i.cbs_response,
			i.cbs_status,
			i.branch,
			i.branch_code,
			d.transaction_id cbs_transaction_id,
			d.service_type,
			d.fee_charges,
			d.gst,
			d.total_amount,
			( case when d.require_adjustment = 1 then 'Yes' else 'No' end ) require_adjustment,
			( case when d.require_adjustment = 1 then concat(i.branch_code, d.service_gl_account) else '' end ) as service_gl,
			( case when d.require_adjustment = 1 then concat(i.branch_code, d.gst_gl_account) else '' end ) as gst_gl
		FROM
			`tabGST Invoice` i, `tabGST Invoice Item` d
		WHERE
			i.name = d.parent and i.docstatus = 1
		{condition_sql}
		ORDER BY
			i.name DESC, i.posting_date DESC
	"""

	data = frappe.db.sql(query, filters, as_dict=True)
	return data

def get_columns(filters):
	columns = [
		{
			"label": "Invoice Date",
			"fieldname": "invoice_date",
			"fieldtype": "Date",
			"width": 120
		},
		{
			"label": "Invoice Number",
			"fieldname": "invoice_number",
			"fieldtype": "Data",
			"width": 150
		},
		{
			"label": "Service Type",
			"fieldname": "service_type",
			"fieldtype": "Data",
			"width": 100
		},
		{
			"label": "Customer",
			"fieldname": "customer",
			"fieldtype": "Data",
			"width": 200
		},
		{
			"label": "Customer TPN",
			"fieldname": "customer_tpn",
			"fieldtype": "Data",
			"width": 80
		},
		{
			"label": "Customer CID",
			"fieldname": "customer_id",
			"fieldtype": "Data",
			"width": 120
		},
		{
			"label": "CBS Response",
			"fieldname": "cbs_response",
			"fieldtype": "Data",
			"width": 120
		},
		{
			"label": "CBS Status",
			"fieldname": "cbs_status",
			"fieldtype": "Data",
			"width": 250
		},
		{
			"label": "Branch",
			"fieldname": "branch",
			"fieldtype": "Data",
			"width": 100
		},
		{
			"label": "Branch Code",
			"fieldname": "branch_code",
			"fieldtype": "Data",
			"width": 100
		},
		{
			"label": "CBS Transaction ID",
			"fieldname": "cbs_transaction_id",
			"fieldtype": "Data",
			"width": 100
		},
		{
			"label": "Fee Charges",
			"fieldname": "fee_charges",
			"fieldtype": "Currency",
			"width": 100
		},
		{
			"label": "GST",
			"fieldname": "gst",
			"fieldtype": "Currency",
			"width": 100
		},
		{
			"label": "Total Amount",
			"fieldname": "total_amount",
			"fieldtype": "Currency",
			"width": 100
		},
		{
			"label": "Require Adjustment",
			"fieldname": "require_adjustment",
			"fieldtype": "Data",
			"width": 80
		},
		{
			"label": "Service GL Account",
			"fieldname": "service_gl",
			"fieldtype": "Data",
			"width": 80
		},
		{
			"label": "GST GL Account",
			"fieldname": "gst_gl",
			"fieldtype": "Data",
			"width": 80
		},
	]
	return columns
