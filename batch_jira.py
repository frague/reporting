from rabbithole import *



multiline = re.compile('"([^"]+)"', re.MULTILINE)

def reNewLine(matchObj):
	return matchObj.group(1).replace("\n", "\\\\")

def deNewLine(text):
	return text.replace("\\\\", " \\n ").replace('"', "")

def makePriority(p):
	if p == "P1":
		return "Critical"
	return "Major"

tasks = multiline.sub(reNewLine, ReadFile("Tasks.txt"))

'''soap = SOAPpy.WSDL.Proxy(config["jira_soap"])
jiraAuth = soap.login(config["jira"]["user"], config["jira"]["password"])
newissue = soap.createIssue(jiraAuth, {"project": "TORS", "type": 1, "summary": "jdhfkjshdk"})'''











#i = 0
for line in re.split("\n", tasks):
	columns = line.split("	")
	if len(columns) == 7 and columns[2] != "":
		[Sig, Subject, Actions, ExpectedResult, Priority, Estimate, Comments] = columns
#		i = i + 1
#		if i < 5:
#			newissue = soap.createIssue(jiraAuth, {"project": "TORS", "type": "Task", "fixVersions": "Code Hardening", "summary": "%s: %s" % (Sig, Subject), "description": "*Actions*:\n%s\n\n*Expected Result*:\n%s\n\n*Estimate*: %s\n\n*Comments*: %s" % (deNewLine(Actions), deNewLine(ExpectedResult), Estimate, deNewLine(Comments)), "priority": makePriority(Priority), "estimate": Estimate})
#			newissue = soap.createIssue(jiraAuth, {"project": "TORS", "type": 1, "fixVersions": "Code Hardening", "summary": "jdhfkjshdk"})
		print "--- %s: %s, %s, %s, %s, (%s) %s" % (Sig, Subject, deNewLine(Actions), deNewLine(ExpectedResult), makePriority(Priority), Estimate, deNewLine(Comments))
#		GetJira({"action": "createIssue", "project": "TORS", "type": "Task", "fixVersions": "Code Hardening", "summary": "%s: %s" % (Sig, Subject), "description": "*Actions*: \\n %s \\n  \\n *Expected Result*: \\n %s \\n  \\n *Estimate*: %s \\n  \\n *Comments*: %s" % (deNewLine(Actions), deNewLine(ExpectedResult), Estimate, deNewLine(Comments)), "priority": makePriority(Priority)})
