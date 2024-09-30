# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
import json
from frappe.model.document import Document
from frappe.utils import validate_email_address

class InternalClearance(Document):

    def validate(self):
        self.checkUsers()
        self.isApproved()
        
    def on_submit(self):
        
        ictcr_= self.ictcr_clearance==1 or self.ictcr_remarks is not None
        icthr_= (self.icthr_clearance==1 or self.icthr_remarks is not None)
        afd_= (self.afd_clearance==1 or self.afd_remarks is not None)
        iad_= (self.iad_clearance==1 or self.iad_remarks is not None)
        
        emaildict=frappe.db.sql("select u.name from `tabUser` as u INNER JOIN `tabHas Role` as hr ON u.name=hr.parent where hr.role='Audit User' or hr.role='Auditor Manager' ", as_dict=True)
        emaillist=[val.name for val in emaildict]
        
        emailstring=validate_email_address(",".join(emaillist))
        auditlist=emailstring.split(",")
        
        blocks = [auditlist[i:i+20] for i in range(0, len(auditlist), 20)]
        if self.ictcr_clearance==1 and self.icthr_clearance==1 and self.afd_clearance==1 and self.iad_clearance==1:
            for bloc in blocks:
                frappe.sendmail(
                    recipients=bloc,
                    subject='The Internal Clearance has been approved by approvers for {}'.format(self.employee_name),
                    message='Dear Sir or Madam\nThere Internal Audit Clearance For Name: {uname} Designation: {designation} of Branch: {branch} for the purpose {purpose} has been approved by relevant approvers. Get the print and take to CEO for signature\n\n Thank you\nPlease Do not reply to the email'.format(uname=self.employee_name, designation=self.designation, purpose=self.purpose, branch=self.branch),
                    
                )
            
    def isApproved(self):
        
        ictcr_= self.ictcr_clearance==1 or self.ictcr_remarks is not None
        icthr_= (self.icthr_clearance==1 or self.icthr_remarks is not None)
        afd_= (self.afd_clearance==1 or self.afd_remarks is not None)
        iad_= (self.iad_clearance==1 or self.iad_remarks is not None)
        
        
        owner_email=frappe.db.sql("select company_email from `tabEmployee` where name='{}' ".format(self.employee), as_dict=True)[0].company_email
        
        if ictcr_ and icthr_ and afd_ and iad_:
            if self.ictcr_clearance==1 and self.icthr_clearance==1 and self.afd_clearance==1 and self.iad_clearance==1:
                
                frappe.sendmail(
                    recipients=owner_email,
                    subject='The Internal Clearance has been Approved by approvers. ',
                    message='Dear Sir or Madam\nThe Internal Audit Clearance has been approved by approveds. Please SUBMIT your for further validation{purpose}\n\n Thank you\nPlease Do not reply to the email'.format(uname=uname, designation=designation, purpose=purpose, branch=branch),
                    
                )
            else:
                frappe.sendmail(
                    recipients=owner_email,
                    subject='Your Internal Audit Clearance has been disapproved',
                    message="Dear Sir or Madam\nYour Internal Audit Clearance has been disapproved \n\n Thank you\nPlease Do not reply to the email",
                    
                )
                

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

def get_permission_query_conditions(user):
    if not user: user = frappe.session.user
    user_roles = frappe.get_roles(user)

 
    if user == "Administrator":
        return
    
    res=frappe.db.sql("Select division, department from `tabEmployee` where company_email='{}' limit 1".format(user), as_dict=True)
    
    division = res[0].get('division') if len(res)>0 else ""
    department = res[0].get('department') if len(res)>0 else ""
    
    if "GM" in user_roles and (division=="HR & Logistics Division - BDBL" or department=="Operations Department - BDBL'  LIMIT 1" or division=="Finance & Accounts Division - BDBL" or division=="Internal Audit  - BDBL"):
        return
    
    if "HR User" in user_roles or "HR Manager" in user_roles or  "Audit User" in user_roles or "Auditor Manager" in user_roles :
        return

    return """(
        `tabInternal Clearance`.owner = '{user}' 
    )""".format(user=user)
            

        


        

        
