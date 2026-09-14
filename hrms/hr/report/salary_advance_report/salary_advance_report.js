// Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Salary Advance Report"] = {
	"filters": [
		{
            'fieldname': 'name',
            'label': 'Reference Name',
            'fieldtype': 'Link',
            'options': 'Employee Advance',
			'link' : 'id'
        },
		{
            'fieldname': 'branch',
            'label': 'Branch',
            'fieldtype': 'Link',
            'options': 'Branch'
        },
       
		 {
            'fieldname': 'recovery_start_date',
            'label': 'Recovery Start Date',
            'fieldtype': 'Date',
            'options': 'Recovery Start Date'
        },
		 {
            'fieldname': 'recovery_end_date',
            'label': 'Recovery End Date',
            'fieldtype': 'Date',
            'options': 'Recovery End Date'
        },

	]
};
