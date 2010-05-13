from rabbithole import *

#############################################################

issuesExpr = re.compile('((^|\n)([^|]+\|){8}[^|\n]+)', re.MULTILINE)

def appendIssue(matchObj):
	global cqKeys

	issue = matchObj.group(1).strip().split("|")
	if len(cqKeys) == 0:
		cqKeys = issue
	else:
		i = {}
		k = 0
		for key in cqKeys:
			i[cqKeys[k]] = issue[k]
			k = k + 1
		if (i["Assigned_To"] == "tgautier"):
			cqIssues["%s: %s" % (i["id"], i["Title"])] = i

	return ""


#############################################################

class JiraIssue:
	global soap, jiraAuth, config

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

	def Resolve(self):
		if self.IsNotEmpty():
			soap.progressWorkflowAction(jiraAuth, self.key, '2', [{"id": "resolution", "values": "2"}])




ProfileNeeded()

cqKeys = []
cqIssues = {}
issuesExpr.sub(appendIssue, ReadFile("cqt.txt"))


soap = SOAPpy.WSDL.Proxy(config["jira_soap"])
jiraAuth = soap.login(config["jira"]["user"], config["jira"]["password"])

issue = JiraIssue()
issues = soap.getIssuesFromFilter(jiraAuth, "11180")



for i in issues:
	issue.Parse(i)
	action = "-"
	if (cqIssues.has_key(issue.summary)):	# Existing issue
		if issue.status != "6":	# Not closed issues
			i = cqIssues[issue.summary]
			if i["State"] == "Closed" or i["State"] == "Verify":
				action = "Resolve"
				issue.Resolve()
		del cqIssues[issue.summary]

	print "[%s] %s" % (action, issue.summary)


# Create new issues
for i in cqIssues.keys():
	v = cqIssues[i]

	if v["State"] != "Closed" and v["State"] != "Verify":
		descr = re.sub("([^>])(\n<)", "\\1{code}\\2", v["Steps_Description"])
		descr = re.sub("(>\n)([ \t]*[^< \t])", "\\1{code}\\2", descr)

		newIssue = soap.createIssue(jiraAuth, {"project": config["project_abbr"], "type": "1", "priority": v["Priority"][0:1], "summary": "%s: %s" % (v["id"], v["Title"]), "description": descr, "assignee": "oaravin", "reporter": "bdaftardar"})
		soap.updateIssue(jiraAuth, newIssue.key, [{"id": "fixVersions", "values": ["10698"]}])

		print "[Created] %s: %s" % (v["id"], v["Title"])


'''
for i in issues:
	issue.Parse(i)
	n = issue.Number()

	print "%s: %s" % (issue.key, issue.status)

	if (issue.status != "6"):
		if n >= 645 and n <=716:
			issue.Update([{"id": "fixVersion", "values": ["10721", "10725"]}])

		if n > 716 and n <=762:
			issue.Update([{"id": "fixVersion", "values": ["10721", "10726"]}])'''

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