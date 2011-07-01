from rabbithole import *


local = {}

ProfileNeeded()


soap = SOAPpy.WSDL.Proxy(config["jira_soap"])
jiraAuth = soap.login(config["jira"]["user"], config["jira"]["password"])

print "\n--- Getting versions and components: -----------------------"

versionId = None
backlogVersionId = None
for v in soap.getVersions(jiraAuth, config["project_abbr"]):
	if v["name"] == config["current_version"]:
		versionId = v["id"]
	if v["name"] == "Product Backlog":
		backlogVersionId = v["id"]

if not versionId or not backlogVersionId:
	print "[!] jira version is not found!"
	exit(1)

componentId = None
for co in soap.getComponents(jiraAuth, config["project_abbr"]):
	if co["name"] == config["jira_sync_component"]:
		componentId = co["id"]

if not componentId:
	print "[!] jira component is not found!"
	exit(1)

print "\n--- Reading local jira tasks -------------------------------"

for i in soap.getIssuesFromJqlSearch(jiraAuth, "project = \"%s\" AND component=\"%s\"" % (config["project_abbr"], config["jira_sync_component"]), 1000):
	issue = JiraIssue()
	issue.Parse(i)
	if issue.IsNotEmpty() and issue.environment:
		local[issue.environment] = issue

print "%s issue(s) loaded." % len(local)

print "\n--- Reading remote jira tasks ------------------------------"

remoteSoap = SOAPpy.WSDL.Proxy(config["jira_remote"]["soap"])
remoteJiraAuth = remoteSoap.login(config["jira_remote"]["user"], config["jira_remote"]["password"])

def CheckAssignee(assignee):
	global config

	if assignee not in config["logins_names"].keys():
		return config["QAAssignee"]
	return assignee

def TryWorkflowAction(issue, action, message):
	global log

	log += "      Action \"%s\" (%s): " % (message, action)
	try:
		issue.DoAction(action)
		log += "Passed\n"
		return True
	except:
		log += "Passed\n"
	return False


actions = {"11": "Assign to development", "41": "Resolve without build", "61": "Build successful", "101": "Tests passed"}

# Reading issues from remote jira
for i in remoteSoap.getIssuesFromJqlSearch(remoteJiraAuth, config["jira_query"], 1000):
	issue = JiraIssue()
	issue.Parse(i)

	# Detailed description custom field
	issue.description = issue.GetCustomField("customfield_10240")
	issue.MakeCodeSections("xml")

	if not issue.IsNotEmpty():
		continue
		
	action = " "
	if local.has_key(issue.key):
		localIssue = local[issue.key]

		# Check whether issues are equal
		if localIssue.IsClosed():
			if not issue.IsClosed():
#				print "    Closing remote (%s) - %s" % (issue.key, issue.assignee)
				issue.Connect(remoteSoap, remoteJiraAuth)

				if not issue.assignee:
					# Assign first
					issue.Update([{"id": "assignee", "values": [config["QAAssignee"]]}])

				log = ""
				result = False
				for a in sorted(actions.iterkeys()):
					result = result or TryWorkflowAction(issue, a, actions[a])
				if result:						
					action = "X"
				else:
					print "    Error closing issue %s\n%s" % (issue.key, log)
					action = "!"
		else:
			if issue.IsClosed():
#				print "    Closing local (%s)" % localIssue.key
				localIssue.Connect(soap, jiraAuth)
				localIssue.Close()
				action = "x"
			else:
				if issue.summary != localIssue.summary or issue.description != localIssue.description:
					localIssue.Connect(soap, jiraAuth)
					localIssue.Update([{"id": "summary", "values": [issue.summary]}, {"id": "description", "values": [issue.description]}])
					action = "@"

   	else:
   		# Create new issue in local jira
   		issue.Connect(soap, jiraAuth)
   		issue.project = config["project_abbr"]
   		issue.type = "1"
   		issue.issuetype = "1"

   		issue.assignee = CheckAssignee(issue.assignee)
	   		 
   		issue.reporter = "nbogdanov"
   		issue.environment = i.key
   		issue.key = ""
   		issue.Create()

		if issue.key:
			issue.SetVersion([versionId, backlogVersionId])
			issue.SetComponent([componentId])

		action = "+"

   	print "[%s] (%s) %s" % (action, issue.key, issue.summary[0:80])








print "\nDone!"
