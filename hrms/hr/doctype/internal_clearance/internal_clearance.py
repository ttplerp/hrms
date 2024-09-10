# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
import json
from frappe.model.document import Document

class InternalClearance(Document):

    def validate(self):
        

        self.checkUsers()

    def checkUsers(self):

        gmhr=frappe.db.sql("select u.name from `tabUser` as u INNER JOIN `tabHas Role` as hr ON u.name=hr.parent INNER JOIN `tabEmployee` as e ON u.name=e.company_email where hr.role='GM' and e.division='HR & Logistics Division - BDBL' LIMIT 1")
        gmcr=frappe.db.sql("select u.name from `tabUser` as u INNER JOIN `tabHas Role` as hr ON u.name=hr.parent INNER JOIN `tabEmployee` as e ON u.name=e.company_email where hr.role='GM' and e.department='Operations Department - BDBL'  LIMIT 1")
        gmfinance=frappe.db.sql("select u.name from `tabUser` as u INNER JOIN `tabHas Role` as hr ON u.name=hr.parent INNER JOIN `tabEmployee` as e ON u.name=e.company_email where hr.role='GM' and e.division='Finance & Accounts Division - BDBL' LIMIT 1")
        gmiad=frappe.db.sql("select u.name from `tabUser` as u INNER JOIN `tabHas Role` as hr ON u.name=hr.parent INNER JOIN `tabEmployee` as e ON u.name=e.company_email where hr.role='GM' and e.division='Internal Audit  - BDBL' LIMIT 1")
        self.icthr=gmhr if gmhr else ""
        self.ictcr=gmcr if gmcr else ""
        self.afd=gmfinance if gmfinance else ""
        self.iad=gmiad if gmiad else ""
  
@frappe.whitelist()
def sendemail(emails,  uname, designation, purpose, branch):
    arr=json.loads(emails)
    #frappe.throw(str(list(arr.values())))
    try:
        frappe.sendmail(
            recipients=list(arr.values()),
            subject='Waiting for Approval for Internal Audit Clearance',
            message='Dear Sir or Madam\nThere is a waiting approval for Internal Audit Clearance For Name: {uname} Designation: {designation} of Branch: {branch} for the purpose {purpose}\n\n Thank you\nPlease Do not reply to the email'.format(uname=uname, designation=designation, purpose=purpose, branch=branch),
            
        )
        
        
    except Exception:
        frappe.throw(str(Exception))
    
 
@frappe.whitelist()
def setemailcheck(docid):
    frappe.db.set_value('Internal Clearance', docid, 'mail_sent', 1)

        
            

        


        

        
