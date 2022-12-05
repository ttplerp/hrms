import requests

import frappe
from frappe.utils import now_datetime, add_years

from erpnext.setup.utils import enable_all_roles_and_domains

country_info = {}


@frappe.whitelist(allow_guest=True)
def get_country(fields=None):
	global country_info
	ip = frappe.local.request_ip

	if ip not in country_info:
		fields = ["countryCode", "country", "regionName", "city"]
		res = requests.get(
			"https://pro.ip-api.com/json/{ip}?key={key}&fields={fields}".format(
				ip=ip, key=frappe.conf.get("ip-api-key"), fields=",".join(fields)
			)
		)

		try:
			country_info[ip] = res.json()

		except Exception:
			country_info[ip] = {}

	return country_info[ip]


def before_tests():
	frappe.clear_cache()
	# complete setup if missing
	from frappe.desk.page.setup_wizard.setup_wizard import setup_complete

	year = now_datetime().year
	if not frappe.get_list("Company"):
		setup_complete(
			{
				"currency": "INR",
				"full_name": "Test User",
				"company_name": "Wind Power LLC",
				"timezone": "Asia/Kolkata",
				"company_abbr": "WP",
				"industry": "Manufacturing",
				"country": "India",
				"fy_start_date": f"{year}-01-01",
				"fy_end_date": f"{year}-12-31",
				"language": "english",
				"company_tagline": "Testing",
				"email": "test@erpnext.com",
				"password": "test",
				"chart_of_accounts": "Standard",
			}
		)

	enable_all_roles_and_domains()
	frappe.db.commit()  # nosemgrep

def update_employee(employee, details, date=None, cancel=False):
	internal_work_history = {}
	new_pro_date = None
	for a in details:
		next_promotion_years = frappe.db.get_value("Employee Grade",a.new,"next_promotion_years")
		if next_promotion_years and next_promotion_years > 0:
			new_pro_date = add_years(date,int(frappe.db.get_value("Employee Grade",a.new,"next_promotion_years")))
	# details.extend(frappe._dict({'fieldname': 'promotion_due_date', 'new': new_pro_date, 'current': date}))
	setattr(employee, 'promotion_due_date', new_pro_date)
	internal_work_history['promotion_due_date'] = new_pro_date
	for item in details:
		fieldtype = frappe.get_meta("Employee").get_field(item.fieldname).fieldtype
		new_data = item.new if not cancel else item.current
		if fieldtype == "Date" and new_data:
			new_data = getdate(new_data)
		elif fieldtype =="Datetime" and new_data:
			new_data = get_datetime(new_data)
		setattr(employee, item.fieldname, new_data)
		if item.fieldname in ["department", "designation", "branch", "grade", "promotion_due_date"]:
			internal_work_history[item.fieldname] = item.new
			internal_work_history["reference_doctype"] = item.parenttype
			internal_work_history["reference_docname"] = item.parent
	if internal_work_history and not cancel:
		internal_work_history["from_date"] = date
		employee.append("internal_work_history", internal_work_history)
	return employee
