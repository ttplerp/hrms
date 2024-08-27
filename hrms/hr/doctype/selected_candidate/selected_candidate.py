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
		token  = get_token()
		settings = frappe.get_single('TheGateway Connectivity')
		host = settings.host
		organization_id = settings.organization_id		
		# frappe.msgprint(f"token : {orgainzation_id}")
		try:
			headers = {
				'Content-Type': 'application/json',
				'Authorization': 'Bearer '+token
			}
			url = f"{host}/api/erp/integration/organization?organization={organization_id}"
			response = requests.get(url, headers=headers)
			
			if response.status_code == 200:
				content = response.content
				c_root = ET.fromstring(content)
				# Extract the data for each item
				self.set("selected_list",[])
				for item in c_root.findall('item'):
					self.append("selected_list", {
						'citizenship_id': item.find('cid').text if item.find('cid') is not None else None,
						'personal_email': item.find('email').text if item.find('email') is not None else None,
						'full_name': item.find('fullName').text if item.find('fullName') is not None else None,
						'job_title': item.find('jobTitle').text if item.find('jobTitle') is not None else None,
						'user_id': item.find('userId').text if item.find('userId') is not None else None,
						'application_number': item.find('applicantId').text if item.find('applicantId') is not None else None,
						'mobile_number': item.find('mobileNo').text if item.find('mobileNo') is not None else None,
						'gender': item.find('genderText').text if item.find('genderText') is not None else None,
					})
			else:
				content = response.content
				root = ET.fromstring(content)
				message = root.find('message').text
				frappe.throw(f"{message}")
		except requests.exceptions.RequestException as err:
			frappe.throw(_("Unable to connect to TheGateway"), title="Connection Failure")

@frappe.whitelist()
def create_employee(source_name, target_doc=None):
	if not frappe.flags.args and not frappe.flags.args.user_id:
		frappe.throw("Used id not found.")
	
	if not frappe.flags.args and not frappe.flags.args.child_name:
		frappe.throw("Child id not found.")
	
	child_name = frappe.flags.args.child_name
	user_id = frappe.flags.args.user_id	
	token  = get_token()
	
	# fetching url
	settings = frappe.get_single('TheGateway Connectivity')
	host = settings.host
	url = f"{host}/api/erp/integration/selected?userId={user_id}"
	headers_integration = {
		'Content-Type': 'application/json',
		'Authorization': 'Bearer '+token
	}
	response = requests.get(url, headers=headers_integration)
	if response.status_code == 200:
		content = response.content
		root = ET.fromstring(content)
		doclist = get_mapped_doc("Selected Candidate", source_name, {
			"Selected Candidate": {
				"doctype": "Employee",
				"field_map":{
					"posting_date": "date_of_joining"
				},
			},
		}, target_doc)
		doclist.set("salutation", 			root.find('salutation').text if root.find('firstName') is not None else None)
		
		doclist.set("employee_name", 		root.find('fullName').text if root.find('fullName') is not None else None)

		doclist.set("first_name", 			root.find('firstName').text if root.find('firstName') is not None else None)
		doclist.set("middle_name", 			root.find('middleName').text if root.find('middleName') is not None else None)
		doclist.set("last_name", 			root.find('lastName').text if root.find('lastName') is not None else None)
		doclist.set("status", 				"Active")
		doclist.set("date_of_birth",		datetime.datetime.fromtimestamp(cint(root.find('dob').text) / 1000).strftime('%Y-%m-%d') if root.find('dob') is not None else None)
		doclist.set("employment_type", 		root.find('employmentType').text if root.find('employmentType') is not None else None)
		doclist.set("employment_status",	"Probation")
		doclist.set("gender", 				root.find('genderText').text if root.find('genderText') is not None else None)
		doclist.set("grade", 				root.find('grade').text if root.find('grade') is not None else None)
		doclist.set("designation", 			root.find('designation').text if root.find('designation') is not None else None)
		doclist.set("cell_mobile", 			root.find('mobileNo').text if root.find('mobileNo') is not None else None)
		doclist.set("personal_email",		root.find('email').text if root.find('email') is not None else None)
		doclist.set("permanent_address", 	root.find('permanentAddress').text if root.find('permanentAddress') is not None else None)
		doclist.set("current_address", 		root.find('presentAddress').text if root.find('presentAddress').text is not None else None)
		doclist.set("passport_number", 		root.find('cid').text if root.find('cid') is not None else None)
		doclist.set("dzongkhag", 			root.find('dzongkhag').text if root.find('dzongkhag') is not None else None)
		doclist.set("applicant_id", 		root.find('applicantId').text if root.find('applicantId') is not None else None)
		doclist.set("selected_doc", 		child_name)
		qualifications = []
		qualifications_parent = root.find('qualifications')
		for qualification in qualifications_parent.findall('qualifications'):
			qualification_details = {
				"qualification": qualification.find("qualificationType").text if qualification.find('qualificationType') is not None else None,
				"year_of_passing": datetime.datetime.fromtimestamp(cint(qualification.findtext("completionYear")) / 1000).strftime('%Y-%m-%d') if qualification.findtext("completionYear") is not None else None,
				"class_per": qualification.findtext("percentageObtained"),
				"school_univ": qualification.findtext("schoolName"),
			}
			qualifications.append(qualification_details)
		doclist.set("education", qualifications)

		experiences = []
		experiences_parent = root.find('experience')
		for experience in experiences_parent.findall('experience'):
			experience_details = {
				"company_name": 		experience.find("organizationName").text if experience.find('organizationName') is not None else None,
				"designation": 			experience.findtext("designation"),
				"address": 				experience.findtext("workDescription"), 
				"total_experience": 	qualification.findtext("noOfExperience"),
			}
			experiences.append(experience_details)

		doclist.set("external_work_history", experiences)
		return doclist
	else:
		content = response.content
		root = ET.fromstring(content)
		message = root.find('message').text
		frappe.throw(f"{message}")

@ frappe.whitelist()
def update_status(applicant_id, status):
	token  = get_token()
	headers = {
		'Content-Type': 'application/json',
		'Authorization': 'Bearer '+token
	}

	settings = frappe.get_single('TheGateway Connectivity')
	host = settings.host
	url = f"{host}/api/erp/integration/update?applicationId={applicant_id}&applicantStatus={status}"

	response = requests.post(url, headers=headers)

	if response.status_code == 200:
		content = response.content
		frappe.msgprint(f"{content}")
	else :
		content = response.content
		root = ET.fromstring(content)
		message = root.find('message').text
		frappe.throw(f"{message}")

@ frappe.whitelist()
def get_token():
	try:
		settings = frappe.get_single('TheGateway Connectivity')
		host = settings.host
		url = f"{host}/api/auth/signin"
		# frappe.msgprint(f"{url}")
		username = settings.username
		password = settings.get_password('password')
		payload = {
			"username": username,
			"password": password
		}
		headers = {
			'Content-Type': 'application/json'
		}
		response = requests.post(url, data=json.dumps(payload), headers=headers)
		
		if response.status_code == 200:
			response_content = response.content
			root = ET.fromstring(response_content)
			token = ''
			for child in root:
				if child.tag=='accessToken':
					token = child.text
			print(token)
			logger.info('*** Connected to TheGateway successfully...')
			return token
		else:
			logger.exception('Failed to connect to TheGateway')
			frappe.throw(_("Unable to connect to TheGateway"), title="Connection Failure")
	except requests.exceptions.RequestException as err:
		frappe.throw(_("Unable to connect to TheGateway"), title="Connection Failure")