from rabbithole import *


class JiraIssue:
	global soap, jiraAuth

	def __init__(self):
		pass

	def Number(self):
		if self.IsNotEmpty():
			return int(re.sub("[^0-9]", "", self.key))
		else:
			return 0

	def Parse(self, line):
		for key in line._keys():
			setattr(self, key, line[key])
	
	def Clear(self):
		self.id = 0
		self.key = ""

	def IsNotEmpty(self):
		return self.key and self.id

	def Update(self, changes):
		if self.IsNotEmpty():
			soap.updateIssue(jiraAuth, self.key, changes)



ProfileNeeded()

soap = SOAPpy.WSDL.Proxy(config["jira_soap"])
jiraAuth = soap.login(config["jira"]["user"], config["jira"]["password"])

filterName = "CodeHardening2Report"
issue = JiraIssue()

issues = soap.getIssuesFromFilter(jiraAuth, "11198")

for i in issues:
	issue.Parse(i)
	n = issue.Number()

	print "%s: %s" % (issue.key, issue.status)

	if (issue.status != "6"):
		if n >= 645 and n <=716:
			issue.Update([{"id": "fixVersion", "values": ["10721", "10725"]}])

		if n > 716 and n <=762:
			issue.Update([{"id": "fixVersion", "values": ["10721", "10726"]}])

'''if re.search(" same ", issue.summary):
		print "-- %s" % issue.summary
		issue.Update([{"id": "priority", "values": "3"}, {"id": "assignee", "values": "tgautier"}])'''

#		issue.Update([{"id": "priority", "values": "3"}])


'''

[
059.        {"id": "summary", "values": ['[Updated] Issue created with Python'] },
060. 
061.        # Change issue type to 'New feature'
062.        {"id":"issuetype", "values":'2'},
063. 
064.        # Setting a custom field. The id (10010) is discoverable from
065.        # the database or URLs in the admin section
066. 
067.        {"id": "customfield_10010", "values": ["Random text set in updateIssue method"] },
068. 
069.        {"id":"fixVersions", "values":['10331']},
070.        # Demonstrate setting a cascading selectlist:
071.        {"id": "customfield_10061", "values": ["10098"]},
072.        {"id": "customfield_10061_1", "values": ["10105"]},
073.        {"id": "duedate", "values": datetime.date.today().strftime("%d-%b-%y")}
074. 
075.        ]

'''