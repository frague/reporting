from rabbithole import *


class RallyObject(object):
	def __init__(self, node = None):
		if node:
			self.ParseFromXml(node)

	def SubnodeValue(self, node, name):
		sub = node.xpathEval(name)
		if sub:
			return sub[0].content

	def SubnodeProp(self, node, name, prop):
		sub = node.xpathEval(name)
		if sub:
			return sub[0].prop(prop)
	
	def ParseFromXml(self, node):
		self.Node = node

		# Basic properties
		self.ref = node.prop("ref")
		self.Name = node.prop("Name") or node.prop("refObjectName")
		self.Type = node.prop("Type")

		# Extended properties
		self.Id = self.SubnodeValue(node, "FormattedID")
		self.Owner = self.SubnodeProp(node, "Owner", "refObjectName")
		self.Status = self.SubnodeValue(node, "TaskStatus")
		self.Description = self.SubnodeValue(node, "Description")

	def __repr__(self):
		return "[%s] %s" % (self.Id, self.Name)


class RallyRESTFacade(object):
	def __init__(self):
		pm = urllib2.HTTPPasswordMgrWithDefaultRealm()
		pm.add_password(None, config["rally"]["rest"], config["rally"]["user"], config["rally"]["password"])
		handler = urllib2.HTTPBasicAuthHandler(pm)

		opener = urllib2.build_opener(handler)
		urllib2.install_opener(opener)

	def ParseObjects(self, entity, text):
#		print text
		doc = libxml2.parseDoc(text)
		result = {}
		for o in [RallyObject(q) for q in doc.xpathNewContext().xpathEval("//Results/Object[@type='%s']" % entity)]:
			result[o.Name] = o 
		return result	

	def AskFor(self, entity, query, fetch = False):
		url = "%s%s?fetch=%s&query=(%s)" % (config["rally"]["rest"], entity, str(fetch).lower(), urllib.quote(query))
#		print url
		request = urllib2.Request(url)
		return self.ParseObjects(entity, urllib2.urlopen(request).read())

	def AskForIterations(self, project, fetch = False):
		return self.AskFor("Iteration", "Project.Name = \"%s\"" % (project), fetch)

	def AskForUserStories(self, iteration, fetch = False):
		return self.AskFor("HierarchicalRequirement", "Iteration = \"%s\"" % (iteration.ref), fetch)

	def AskForUserStoryTasks(self, user_story, fetch = False):
		return self.AskFor("Task", "WorkProduct = \"%s\"" % (user_story.ref), fetch)

def CreateJiraIssueFrom(rally_issue, parentIssueId):
	global soap, jiraAuth, config

	i = JiraIssue()
	i.Connect(soap, jiraAuth)

	i.parentIssueId = parentIssueId
	i.issuetype = "6"	# TODO!

	i.project = config["project_abbr"]
	i.summary = "(%s) %s" % (rally_issue.Id, rally_issue.Name)
	i.description = rally_issue.Description

	i.Create()
	
###################################################################################################################

ProfileNeeded()

print "--- Reading jira tasks -------------------------------------"

rallyIssueExpr = re.compile("^\(((US|TA)\d+)\) ")
jiraIssues = {}

soap = SOAPpy.WSDL.Proxy(config["jira_soap"])
jiraAuth = soap.login(config["jira"]["user"], config["jira"]["password"])


versionId = None
backlogVersionId = None
for v in soap.getVersions(jiraAuth, config["project_abbr"]):
	if v["name"] == config["current_version"]:
		versionId = v["id"]
	if v["name"] == "Product Backlog":
		backlogVersionId = v["id"]

if not versionId or not backlogVersionId:
	print "[!] jira version is not found!"
	exit(0)


for i in soap.getIssuesFromJqlSearch(jiraAuth, "project = '%s' AND fixVersion = '%s'" % (config["project_abbr"], config["current_version"]), 1000):
	issue = JiraIssue()
	issue.Parse(i)

	key = GetMatchGroup(issue.summary, rallyIssueExpr, 1)
	if key:
		jiraIssues[key] = issue
		print "[ ] %s" % issue.summary



print "\n--- Reading rally tasks ------------------------------------"

rf = RallyRESTFacade()
iterations = rf.AskForIterations("RAS")
stories = rf.AskForUserStories(iterations["Sprint 1 (2/7 - 2/18)"], True)

for us in stories:
	story = stories[us]
	parentIssueId = None
	action = " "
	if not jiraIssues.has_key(tasks[task].Id):
		action = "+"
	else:
		parentIssueId = jiraIssues[tasks[task].Id].id

	print "[%s] %s (%s)" % (action, story, parentIssueId)

	tasks = rf.AskForUserStoryTasks(story, True)
	for task in tasks:
		action = " "
		if not jiraIssues.has_key(tasks[task].Id):
			action = "+"
			#CreateJiraIssueFrom(tasks[task], parentIssueId)

		print " [%s] %s" % (action, tasks[task])
