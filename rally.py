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
		if self.Owner and config["names_logins"].has_key(self.Owner):
			self.Owner = config["names_logins"][self.Owner]
		else:
			self.Owner = ""
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

	def AskForUserStoryDefects(self, user_story, fetch = False):
		return self.AskFor("Defect", "Requirement = \"%s\"" % (user_story.ref), fetch)


replaces = {"&nbsp;": " ", "&lt;": "<", "&gt;": ">", "&amp;": "&"}
def ReformatDescription(text):
	text = re.sub("<br[^>]*>", "\n", text)

	text = DeTag(text)
	for needle in replaces:
		text = text.replace(needle, replaces[needle])

	return text

def CreateJiraIssueFrom(rally_issue, parentIssueKey = "", issueType = None, versions = []):
	global soap, jiraAuth, config

	i = JiraIssue()

	i.project = config["project_abbr"]
	i.assignee = rally_issue.Owner

	i.summary = "(%s) %s" % (rally_issue.Id, rally_issue.Name)
	i.description = rally_issue.Description
	i.MakeCodeSections()

	if re.search("^TA", rally_issue.Id):		# UserStory = Supertask
		i.CreateSubtask(parentIssueKey)
	else:
		i.issuetype = issueType or "6"
		i.Connect(soap, jiraAuth)
		i.Create()

	if i.key:
		i.SetVersion(versions)

	return i

	
###################################################################################################################


ProfileNeeded()

print "--- Reading jira tasks -------------------------------------"

rallyIssueExpr = re.compile("^\(((US|TA|DE)\d+)\) ")
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


for i in soap.getIssuesFromJqlSearch(jiraAuth, "project = '%s' AND (fixVersion = '%s' OR fixVersion = 'Product Backlog')" % (config["project_abbr"], config["current_version"]), 1000):
	issue = JiraIssue()
	issue.Parse(i)

	key = GetMatchGroup(issue.summary, rallyIssueExpr, 1)
	if key:
		jiraIssues[key] = issue
#		print "[ ] %s" % issue.summary



print "\n--- Reading rally tasks ------------------------------------"

rf = RallyRESTFacade()
iterations = rf.AskForIterations("RAS")
stories = rf.AskForUserStories(iterations["Sprint 1 (2/7 - 2/18)"], True)

for us in stories:
	story = stories[us]
	parentIssueId = None
	action = " "
	if not jiraIssues.has_key(story.Id):
		jiraIssues[story.Id] = CreateJiraIssueFrom(story)
		action = "+"
	parentIssueId = jiraIssues[story.Id].key
	print "\n[%s] %s (%s)" % (action, story, parentIssueId)

###### Tasks ######################################################################################	
	tasks = rf.AskForUserStoryTasks(story, True)
	for t in tasks:
		task = tasks[t]
		action = " "
		if not jiraIssues.has_key(task.Id):
			action = "+"
			issue = CreateJiraIssueFrom(task, parentIssueId, None, [versionId, backlogVersionId])
			if not issue.key:
				action = "!"

		print " [%s] %s" % (action, task)

###### Defects ####################################################################################	
	defects = rf.AskForUserStoryDefects(story, True)
	for d in defects:
		defect = defects[d]
		action = " "
		if not jiraIssues.has_key(defect.Id):
			action = "+"
			defect.Description = ReformatDescription(defect.Description)
			issue = CreateJiraIssueFrom(defect, "", "1", [backlogVersionId])
			if not issue.key:
				action = "!"

		print " [%s] %s" % (action, defect)


print "\nDone!"