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
		pass
   	else:
   		issue.Connect(soap, jiraAuth)
   		issue.project = config["project_abbr"]
   		issue.type = "1"
   		issue.issuetype = "1"
   		issue.assignee = config["QAAssignee"]
   		issue.reporter = "nbogdanov"
   		issue.environment = i.key
   		issue.key = ""
   		issue.Create()

		if issue.key:
			issue.SetVersion([versionId, backlogVersionId])
			issue.SetComponent([componentId])

		action = "+"

   	print "[%s] %s" % (action, issue.summary[0:80])








print "\nDone!"
