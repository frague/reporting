from rabbithole import *

#############################################################

line = 80

issuesExpr = re.compile('((id|\nBUILD[0-9]+)(\|[^|]*){8}($|\n))', re.MULTILINE)

total = 0
def appendIssue(matchObj):
	global cqKeys, total

	issue = matchObj.group(1).strip().split("|")
	if len(cqKeys) == 0:
		cqKeys = issue
	else:
		i = {}
		k = 0
		for key in cqKeys:
			i[cqKeys[k]] = re.sub("##NL##", "\n", issue[k]).strip()
			k = k + 1

		total = total + 1
#		print "%s. %s: %s" % (total, i["id"], i["Assigned_To"])
		if (i["Assigned_To"] == "tgautier" or i["Assigned_To"] == "mgorbunov"):
			cqIssues["%s: %s" % (i["id"], i["Title"])] = i

	return ""


#############################################################


ProfileNeeded()

cqKeys = []
cqIssues = {}

issuesExpr.sub(appendIssue, re.sub("(BUILD[0-9]+)", "\n\\1", re.sub("\n", "##NL##", ReadFile(config["QABugsFile"]))))

soap = SOAPpy.WSDL.Proxy(config["jira_soap"])
jiraAuth = soap.login(config["jira"]["user"], config["jira"]["password"])

issue = JiraIssue(soap, jiraAuth)
issues = soap.getIssuesFromJqlSearch(jiraAuth, "project = %s AND fixVersion = QA" % config["project_abbr"], 100)

for i in issues:
	issue.Parse(i)
	action = " "
#	print "--- %s, %s" % (issue.status, issue.summary[0:line])
	if (cqIssues.has_key(issue.summary)):	# Existing issue
		if issue.status != "6" and issue.status != "5":	# Not closed issues
			i = cqIssues[issue.summary]
			if i["State"] == "Closed":
				action = "-"
				issue.Resolve()
		del cqIssues[issue.summary]

	print "[%s] %s" % (action, issue.summary[0:line])


# Create new issues
for i in cqIssues.keys():
	v = cqIssues[i]

	if v["State"] != "Closed":
		descr = re.sub("([^>])(\n<)", "\\1{code}\\2", v["Steps_Description"])
		descr = re.sub("(>\n)([ \t\n]*[^< \t\n])", "\\1{code}\\2", descr)

		print "[+] %s: %s" % (v["id"], v["Title"][0:line])
#		print descr

		newIssue = soap.createIssue(jiraAuth, {"project": config["project_abbr"], "type": "1", "priority": v["Priority"][0:1], "summary": "%s: %s" % (v["id"], v["Title"]), "description": descr, "assignee": config["QAAssignee"], "reporter": "nbogdanov"})
		soap.updateIssue(jiraAuth, newIssue.key, [{"id": "fixVersions", "values": [config["QAVersionId"]]}])



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