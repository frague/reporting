from rabbithole import *

ProfileNeeded()

pageName = "%s Daily Status Update" % today.strftime("%Y-%m-%d")
newsSource = GetWiki({"action": "getNewsSource", "space": config["project_space"], "title": pageName}).replace("News source\n", "")
	
risksExpr = re.compile("\{metadata:Risks\}\n(([^\{]|\{[^m]|\{m[^e]|\{me[^t])*)\n\{metadata\}")
dividerExpr = re.compile("^([\-\#\*]+ )")

risks = GetMatchGroup(newsSource, risksExpr, 1)
if risks:
#	print risks
	divider = GetMatchGroup(risks, dividerExpr, 1)
	if divider:
#		print divider
		soap = SOAPpy.WSDL.Proxy(config["jira_soap"])
		jiraAuth = soap.login(config["jira"]["user"], config["jira"]["password"])
		storeChanges = False

		for risk in risks.split(divider):
			if risk:
				i = JiraIssue()
				i.Connect(soap, jiraAuth)
				i.project = config["project_abbr"]
				i.issuetype = "28"			# Risk
				try:
					(i.summary, i.description) = re.split("\n", risk, 1)
				except:
					i.summary = risk
				i.assignee = config["risk_default_assignee"]
				print "[+] Risk: %s" % i.ToString(80)
				i.Create()
				storeChanges = True


		if storeChanges:
			newsSource = risksExpr.sub("", newsSource)

			print "\n-- Publishing on wiki: -------------------------------------------------"
			WriteFile("temp3.tmp", newsSource)
			GetWiki({"action": "storeNews", "space": config["project_space"], "title": pageName, "file": "temp3.tmp"})
			os.remove("temp3.tmp")

print "Done"
