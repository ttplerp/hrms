from __future__ import unicode_literals
from frappe.model.document import Document
import frappe
import requests
from frappe import _
from frappe.utils import cint
import json
import xml.etree.ElementTree as ET
from frappe.model.mapper import get_mapped_doc
import logging
logging.basicConfig(format='%(asctime)s : %(levelname)s : %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)
import datetime


class SelectedCandidate(Document):
	@frappe.whitelist()
	def get_selected_list(self):
		token = get_token()
		settings = frappe.get_single('TheGateway Connectivity')
		host = settings.host.rstrip('/')
		organization_id = settings.organization_id

		try:
			headers = {
				'Content-Type': 'application/json',
				'Authorization': 'Bearer ' + token
			}
			url = f"{host}/api/erp/integration/organization?organization={organization_id}"
			response = requests.get(url, headers=headers)
			if response.status_code == 200:
				data = response.json()  # parse JSON response
				# clear the existing list first
				self.set("selected_list", [])
				for item in data:
					self.append("selected_list", {
						'citizenship_id': item.get('cid'),
						'personal_email': item.get('email'),
						'full_name': item.get('fullName'),
						'job_title': item.get('jobTitle'),
						'user_id': item.get('userId'),
						'application_number': item.get('id'),
						'mobile_number': item.get('mobileNo'),
						'gender': item.get('gender'),
					})
			else:
				# Handle error response, assume JSON with message field
				try:
					error_data = response.json()
					message = error_data.get('message', 'Unknown error')
				except Exception:
					message = response.text or 'Unknown error'
				frappe.throw(message)
		except requests.exceptions.RequestException:
			frappe.throw(_("Unable to connect to TheGateway"), title="Connection Failure")
def get_full_name(data):
    # Extract values, replacing None with empty string
    first = data.get('firstName') or ''
    middle = data.get('middleName') or ''
    last = data.get('lastName') or ''
    
    # Join only non-empty parts to avoid extra spaces
    return " ".join(part for part in [first, middle, last] if part.strip())

@frappe.whitelist()
def create_employee(source_name, target_doc=None):
	if not frappe.flags.args or not frappe.flags.args.user_id:
		frappe.throw("User id not found.")

	if not frappe.flags.args or not frappe.flags.args.child_name:
		frappe.throw("Child id not found.")

	child_name = frappe.flags.args.child_name
	user_id = frappe.flags.args.user_id    
	token  = get_token()

	settings = frappe.get_single('TheGateway Connectivity')
	host = settings.host
	url = f"{host}/api/erp/integration/selected?userId={user_id}"
	headers_integration = {
		'Content-Type': 'application/json',
		'Authorization': "Bearer "+token
	}

	response = requests.get(url, headers=headers_integration)
	if response.status_code == 200:
		val = response.json()  # parse JSON
		
		doclist = get_mapped_doc("Selected Candidate", source_name, {
			"Selected Candidate": {
				"doctype": "Employee",
				"field_map": {
					"posting_date": "date_of_joining"
				},
			},
		}, 
		target_doc
		)
		data = val.get("data")
		doclist.set("salutation", data.get('salutation'))
		doclist.set("employee_name", get_full_name(data))
		doclist.set("status", "Active")
		doclist.set("date_of_birth", data.get('dob'))
		doclist.set("gender", data.get('gender'))	
		doclist.set("employment_type", data.get('employmentType'))
		doclist.set("employment_status", "Probation")
		doclist.set("grade", data.get('grade'))
		doclist.set("designation", data.get('designation'))
		doclist.set("cell_mobile", data.get('mobileNo'))
		doclist.set("personal_email", data.get('email'))
		doclist.set("permanent_address", data.get('permanentAddress'))
		doclist.set("current_address", data.get('presentAddress'))
		doclist.set("passport_number", data.get('cid'))
		doclist.set("dzongkhag", data.get('dzongkhag'))
		doclist.set("applicant_id", data.get('id'))
		doclist.set("selected_doc", child_name)
		
		# qualifications
		qualifications = []
		for qualification in data.get('qualifications') or []:
			marks = qualification.get("marks")
			simplified_marks = []
			if marks and len(marks) > 0:
				simplified_marks = [{mark["subjectName"]: mark["mark"]} for mark in marks]

			qualifications.append({
				"qualification": qualification.get("qualificationType"),
				"year_of_passing": qualification.get("completionYear"),
				"class_per": qualification.get("percentageObtained"),
				"level": qualification.get("courseName"),
				"school_univ": qualification.get("instituteName"),
				"maj_opt_subj": json.dumps(simplified_marks)
			})
		doclist.set("education", qualifications)
		
		# experiences
		experiences = []
		for experience in data.get('experience') or []:
			experiences.append({
				"company_name": experience.get("organization"),
				"designation": experience.get("designation"),
				"address": experience.get("description"),
				"total_experience": experience.get("noOfExperience"),
			})
		doclist.set("external_work_history", experiences)		
		return doclist.as_dict()
	elif response.status_code == 401:
		frappe.throw("Unauthorized!")
	else:
		try:
			data = response.json()
			message = data.get('message', 'Unknown error')
		except Exception:
			message = response.text
		frappe.throw(message)

@ frappe.whitelist()
def update_status(applicant_id, status):
	token = get_token()
	headers = {
		'Content-Type': 'application/json',
		'Authorization': "Bearer " + token
	}

	settings = frappe.get_single('TheGateway Connectivity')
	host = settings.host
	url = f"{host}/api/erp/integration/update?id={applicant_id}&status={status}"

	response = requests.post(url, headers=headers)

	if response.status_code == 200:
		content = response.json()  # parse JSON response
		message = content.get("message")
		frappe.msgprint(f"{message}")
	else:
		try:
			data = response.json()
			message = data.get('message', 'Unknown error')
		except Exception:
			message = response.text
		frappe.throw(f"{message}")

@ frappe.whitelist()
def get_token():
	try:
		settings = frappe.get_single('TheGateway Connectivity')
		host = settings.host.rstrip('/')
		url = f"{host}/api/auth/signin"
		username = settings.username
		password = settings.get_password('password')
		payload = {
			"email": username,
			"password": password
		}
		headers = {
			'Content-Type': 'application/json'
		}

		response = requests.post(url, json=payload, headers=headers, timeout=10)

		if response.status_code == 200:
			try:
				data = response.json()
			except Exception as e:
				logger.error(f"JSON decode failed: {e}")
				frappe.throw("Invalid JSON response from TheGateway")

			# The token is nested in data["data"]["accessToken"]
			token = data.get("data", {}).get("accessToken")
			if token:
				logger.info("*** Connected to TheGateway successfully...")
				return token
			else:
				logger.error("Access token not found in response")
				frappe.throw("Access token not found in TheGateway response")
		else:
			logger.error(f"TheGateway returned status {response.status_code}: {response.text}")
			frappe.throw(f"Failed to connect to TheGateway: {response.status_code}")

	except requests.exceptions.RequestException as e:
		logger.error(f"Request to TheGateway failed: {e}")
		frappe.throw("Unable to connect to TheGateway")
