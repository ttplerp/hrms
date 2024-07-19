# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _

def execute(filters=None):
    if not filters:
        filters = {}
    columns, data = [], []
    data = get_data(filters)
    if not data:
        return columns, data
    columns = get_columns(data)
    transformed_data = transform_data(data, columns)
    
    chart = get_chart(transformed_data, columns)
    
    return columns, transformed_data, None, chart

def get_data(filters):
    return frappe.db.sql("""
        # SELECT 
        #     cost_center, 
        #     designation, 
        #     COUNT(name) as employee_count 
        # FROM 
        #     `tabEmployee` 
        # WHERE 
        #     status = 'Active' 
        # GROUP BY 
        #     cost_center, 
        #     designation
        
        SELECT 
		e.cost_center,
		dg.name1 as designation,  
		COUNT(e.name) as employee_count
	FROM 
		`tabEmployee` e
	INNER JOIN 
		`tabDesignation` d ON e.designation = d.name
	INNER JOIN 
		`tabDesignation Group` dg ON d.designation_group = dg.name
	WHERE 
		e.status = 'Active'
	GROUP BY 
 e.cost_center,
		dg.name1;
        """, as_dict=True)

def get_columns(data):
    # Extract unique designations to create dynamic columns
    designations = sorted({row['designation'] for row in data})
    columns = [
        _("Cost Center") + ":Link/Cost Center:180",
    ]
    for desi in designations:
        columns.append(_(desi) + "::120")
    columns.append(_("Total") + "::120")
    return columns

def transform_data(data, columns):
    # Create a mapping from cost center to designations and their counts
    cost_center_map = {}
    for row in data:
        cost_center = row['cost_center']
        designation = row['designation']
        count = row['employee_count']
        if cost_center not in cost_center_map:
            cost_center_map[cost_center] = {'total': 0}
        cost_center_map[cost_center][designation] = count
        cost_center_map[cost_center]['total'] += count

    # Prepare the final data structure for the report
    transformed_data = []
    for cost_center, desi_counts in cost_center_map.items():
        row = [cost_center]
        for col in columns[1:-1]:  # Skip the first (Cost Center) and last column (Total)
            designation = col.split("::")[0]
            row.append(desi_counts.get(designation, 0))
        row.append(desi_counts['total'])
        transformed_data.append(row)

    return transformed_data

def get_chart(data, columns):
    labels = [row[0] for row in data]  # Cost centers
    totals = [row[-1] for row in data]  # Totals

    chart = {
        "data": {
            "labels": labels,
            "datasets": [
                {
                    "name": _("Total Employees"),
                    "values": totals
                }
            ]
        },
        "type": "bar",
        "axisOptions": {
            "xIsSeries": True
        }
    }

    return chart
