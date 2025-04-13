frappe.query_reports["Salary Register"] = {
	filters: [
		{
			fieldname: "fiscal_year",
			fieldtype: "Link",
			options: "Fiscal Year",
			label: __("Fiscal Year"),
			width: "100px",
		},
		{
			fieldname: "month",
			label: __("Month"),
			fieldtype: "Select",
			options: ['','01', '02', '03', '04', '05', '06', '07', '08', '09', '10', '11', '12'],
			width: "100px",
		},
		{
			fieldname: "employee",
			label: __("Employee"),
			fieldtype: "Link",
			options: "Employee",
			width: "100px",
		},
		{
			fieldname: "company",
			label: __("Company"),
			fieldtype: "Link",
			options: "Company",
			default: frappe.defaults.get_user_default("Company"),
			width: "100px",
			reqd: 1,
		},
		{
			fieldname: "docstatus",
			label: __("Document Status"),
			fieldtype: "Select",
			options: ["Draft", "Submitted", "Cancelled"],
			default: "Submitted",
			width: "100px",
		},
	],
};
