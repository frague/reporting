from rabbithole import *


class RallyObject(object):
	def __init__(self, node = None):
		if node:
			self.ParseFromXml(node)

	def SubnodeValue(self, node, name):
		sub = node.xpathEval(name)
		if sub:
			return sub[0].content
		return ""

	def SubnodeProp(self, node, name, prop):
		sub = node.xpathEval(name)
		if sub:
			return sub[0].prop(prop)
		return ""

	def IsCompleted(self):
		return self.Status == "completed" or self.Status == "accepted"
	
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

		self.Status = (self.SubnodeValue(node, "TaskStatus") or self.SubnodeValue(node, "State")).lower()
		self.Description = self.SubnodeValue(node, "Description")
		self.RevisionHistory = self.SubnodeProp(node, "RevisionHistory", "ref")
		self.CreationDate = self.SubnodeValue(node, "CreationDate")
		if self.CreationDate:
			self.CreationDate = datetime.datetime.strptime(self.CreationDate, "%Y-%m-%dT%H:%M:%S.%fZ").date()

		self.User = self.SubnodeProp(node, "User", "refObjectName")

	def __repr__(self):
		return "[%s] %s (%s)" % (self.Id, self.Name, self.ref)


class RallyRESTFacade(object):
	def __init__(self):
		pm = urllib2.HTTPPasswordMgrWithDefaultRealm()
		pm.add_password(None, config["rally"]["rest"], config["rally"]["user"], config["rally"]["password"])
		handler = urllib2.HTTPBasicAuthHandler(pm)

		opener = urllib2.build_opener(handler)
		urllib2.install_opener(opener)

	def ParseObjects(self, entity, text):
		doc = libxml2.parseDoc(text)
		result = {}
		for o in [RallyObject(q) for q in doc.xpathNewContext().xpathEval("//Results/Object[@type='%s']" % entity)]:
			result[o.Name] = o 
		return result	

	def ParseCollectionObjects(self, path, text):
		doc = libxml2.parseDoc(text)
		result = {}
		for o in [RallyObject(q) for q in doc.xpathNewContext().xpathEval(path)]:
			result[o.ref] = o
		return result	

	def ParseFetchedXml(self, entity, url, debug = False):
		request = urllib2.Request(url)
		text = urllib2.urlopen(request).read()
		if debug:
			#print url
			print text
		return self.ParseObjects(entity, text)
	
	def ParseFetchedCollectionXml(self, entity, url, debug = False):
		request = urllib2.Request(url)
		text = urllib2.urlopen(request).read()
		if debug:
			#print url
			print text
		return self.ParseCollectionObjects(entity, text)
	

	
	
	
	def AskFor(self, entity, query, fetch = False):
		return self.ParseFetchedXml(entity, "%s%s?fetch=%s&query=(%s)" % (config["rally"]["rest"], entity, str(fetch).lower(), urllib.quote(query)))




	def AskForIterations(self, project, fetch = False):
		return self.AskFor("Iteration", "Project.Name = \"%s\"" % (project), fetch)

	def AskForUserStories(self, iteration, fetch = False):
		return self.AskFor("HierarchicalRequirement", "Iteration = \"%s\"" % (iteration.ref), fetch)

	def AskForUserStoryTasks(self, user_story, fetch = False):
		return self.AskFor("Task", "WorkProduct = \"%s\"" % (user_story.ref), fetch)

	def AskForUserStoryDefects(self, user_story, fetch = False):
		return self.AskFor("Defect", "Requirement = \"%s\"" % (user_story.ref), fetch)

	def GetRevisionHistory(self, ref):
		return self.ParseFetchedCollectionXml("//RevisionHistory/Revisions/Revision[@type='Revision']", ref, True)


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


def ProcessTasksFor(story, issue, kind):
	global versionId, backlogVersionId, parentIssueId, jiraIssues, soap, jiraAuth, worklogs, rf

	if kind:
		tasks = rf.AskForUserStoryTasks(story, True)
	else:
		tasks = rf.AskForUserStoryDefects(story, True)

	for t in tasks:
		task = tasks[t]
		action = " "
		if not jiraIssues.has_key(task.Id):
			action = "+"
			if issue.IsClosed():
				action = "/"
			else:
				if kind:
					i = CreateJiraIssueFrom(task, parentIssueId, None, [versionId, backlogVersionId])
				else:
					i = CreateJiraIssueFrom(task, "", "1", [backlogVersionId])

				if not i.key:
					action = "!"
		else:
			ji = jiraIssues[task.Id]
#			print "%s vs. %s"  % (task.IsCompleted(), ji.IsClosed())

			if task.IsCompleted():
				if not ji.IsClosed():
					ji.Connect(soap, jiraAuth)
					ji.Close()
					action = "x"
				else:
					action = "v"
			else:
				if ji.IsClosed():
					action = "?"

		if action != "+" and worklogs.has_key(task.Id) and task.RevisionHistory:
			# Checking worklogs
			print "  In jira: %s" % worklogs[task.Id]
			history = rf.GetRevisionHistory(task.RevisionHistory)
			print "  %s" % history



		print " [%s] %s (%s)" % (action, task, task.Status)
#		print "      %s" % (task.RevisionHistory)




	
###################################################################################################################


ProfileNeeded()

print "--- Reading jira worklogs ----------------------------------"
worklogs = GetWorkLogs(lastWorkday, today, WorklogForRally)


print "\n--- Reading jira tasks -------------------------------------"

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
		jiraIssues[story.Id] = CreateJiraIssueFrom(story, "", "6", [versionId, backlogVersionId])
		action = "+"

	issue = jiraIssues[story.Id]
	parentIssueId = issue.key
	print "\n[%s] %s (%s)" % (action, story, parentIssueId)

###### Tasks ######################################################################################	
	ProcessTasksFor(story, issue, 1)

###### Defects ####################################################################################	
	ProcessTasksFor(story, issue, 0)


print "\nDone!"