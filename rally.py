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
		return self.Status == "COMPLETED" or self.Status == "ACCEPTED" or self.Status == "Completed" or self.Status == "Accepted"
	
	def ParseFromXml(self, node):
		self.node = node

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

		self.Status = (self.SubnodeValue(node, "TaskStatus") or self.SubnodeValue(node, "State"))
		self.Description = self.SubnodeValue(node, "Description")
		self.RevisionHistory = self.SubnodeProp(node, "RevisionHistory", "ref")
		self.CreationDate = self.SubnodeValue(node, "CreationDate")
		if self.CreationDate:
			self.CreationDate = datetime.datetime.strptime(self.CreationDate, "%Y-%m-%dT%H:%M:%S.%fZ").date()

		self.User = self.SubnodeProp(node, "User", "refObjectName")

		self.Actuals = float(self.SubnodeValue(node, "Actuals") or "0")
		self.ToDo = float(self.SubnodeValue(node, "ToDo") or "0")

	def Save(self, fields):
		if not self.ref or not self.Type:
			return False

		doc = libxml2.newDoc("1.0")
		root = doc.newChild(None, self.Type, None)
		root.setNsProp(None, "ref", self.ref)
		
		for field in fields:
			root.newChild(None, field, str(getattr(self, field)))

		#print doc
		headers = {"Content-type": "text/xml"}
		request = urllib2.Request(self.ref, str(doc), headers)

		text = urllib2.urlopen(request).read()
		#doc = libxml2.parseDoc(text) 
		return text

	def Close(self):
		self.Status = "Completed"
		if re.search("^[A-Z\- ]+$", self.Status):
			self.Status = "COMPLETED"
		self.Save(["Status"])
		
	def __repr__(self):
		return "[%s] %s (%s)" % (self.Id, self.Name, self.ref)


class RallyRESTFacade(object):
	def __init__(self):
		pm = urllib2.HTTPPasswordMgrWithDefaultRealm()
		pm.add_password(None, config["rally"]["rest"], config["rally"]["user"], config["rally"]["password"])
		handler = urllib2.HTTPBasicAuthHandler(pm)

		opener = urllib2.build_opener(handler)
		urllib2.install_opener(opener)


	
	# Parse Objects from XML
	def ParseObjectsBase(self, entity, path, text):
		doc = libxml2.parseDoc(text)
		result = {}
		for o in [RallyObject(q) for q in doc.xpathNewContext().xpathEval(path)]:
			if not o.Type:
				o.Type = entity
			result[o.ref] = o
		return result	

	def ParseObjects(self, entity, text):
		return self.ParseObjectsBase(entity, "//Results/Object[@type='%s']" % entity, text)


	# Requesting xml representation of object(s)
	def RequestXml(self, entity, url, debug = False):
		request = urllib2.Request(url)
		text = urllib2.urlopen(request).read()
		if debug:
			#print url
			print text
		return self.ParseObjects(entity, text)
	
	# Requesting xml representation of object(s) by custom path
	def RequestCollectionXml(self, entity, url, path, debug = False):
		request = urllib2.Request(url)
		text = urllib2.urlopen(request).read()
		if debug:
			#print url
			print text
		return self.ParseObjectsBase(entity, path, text)
	
	
	
	# Asking for specific types of objects
	def AskFor(self, entity, query, fetch = False, debug = False):
		return self.RequestXml(entity, "%s%s?fetch=%s&query=(%s)" % (config["rally"]["rest"], entity, str(fetch).lower(), urllib.quote(query)), debug)

	def AskForIterations(self, project, fetch = False):
		return self.AskFor("Iteration", "Project.Name = \"%s\"" % (project), fetch)

	def AskForUserStories(self, iteration, fetch = False):
		return self.AskFor("HierarchicalRequirement", "Iteration = \"%s\"" % (iteration.ref), fetch)

	def AskForUserStoryTasks(self, user_story, fetch = False):
		return self.AskFor("Task", "WorkProduct = \"%s\"" % (user_story.ref), fetch)

	def AskForUserStoryDefects(self, user_story, fetch = False):
		return self.AskFor("Defect", "Requirement = \"%s\"" % (user_story.ref), fetch)

	def GetRevisionHistory(self, ref):
		return self.RequestCollectionXml("Revision", ref, "//RevisionHistory/Revisions/Revision[@type='Revision']")


# Reformats issue description
replaces = {"&nbsp;": " ", "&lt;": "<", "&gt;": ">", "&amp;": "&"}
def ReformatDescription(text):
	text = re.sub("<br[^>]*>", "\n", text)

	text = DeTag(text)
	for needle in replaces:
		text = text.replace(needle, replaces[needle])

	return text

# Creates jira issue from Rally issue
def CreateJiraIssueFrom(rally_issue, parentIssueKey = "", issueType = None, versions = []):
	global soap, jiraAuth, config

	i = JiraIssue()

	i.project = config["project_abbr"]
	i.assignee = rally_issue.Owner

	i.summary = "(%s) %s" % (rally_issue.Id, rally_issue.Name)
	i.description = rally_issue.Description
	i.description = ReformatDescription(i.description)
	i.MakeCodeSections("xml")

	if re.search("^TA", rally_issue.Id):		# UserStory = Supertask
		i.CreateSubtask(parentIssueKey)
	else:
		i.issuetype = issueType or "6"
		i.Connect(soap, jiraAuth)
		i.Create()

	if i.key:
		i.SetVersion(versions)

	return i

actualsAddedExpr 	= re.compile("ACTUALS added \[(\d+\.\d+) Hours{0,1}\]")
actualsChangedExpr 	= re.compile("ACTUALS changed from \[(\d+\.\d+) Hours{0,1}\] to \[(\d+\.\d+) Hours{0,1}\]")
todoAddedExpr 		= re.compile("TO DO added \[(\d+\.\d+) Hours{0,1}\]")
todoChangedExpr 	= re.compile("TO DO changed from \[(\d+\.\d+) Hours{0,1}\] to \[(\d+\.\d+) Hours{0,1}\]")

# Progresses/closes single task by its jira representation
def UpdateProgressFor(task, task_history, reported_in_jira):
	global lastWorkingDay

	progressDateExpr	= re.compile("Progress for (%s)" % lastWorkingDay)
	jiraWork = float(reported_in_jira) / 3600	# Logged work in hours

	syncReported = 0

	# Calculate Rally progress
	for ref in task_history:
		rev = task_history[ref]

		spent = float(GetMatchGroup(rev.Description, actualsAddedExpr, 1) or "0")
		if not spent:
			m = actualsChangedExpr.search(rev.Description)
			if m:
				spent = float(m.group(2)) - float(m.group(1))
		
		if progressDateExpr.search(rev.Description):
			syncReported += spent
		#print " * (%s) Synced=%s	%s [%s, %s]" % (spent, syncReported, rev.Description, rev.CreationDate.strftime("%Y-%m-%d"), lastWorkingDay)

	if jiraWork > syncReported:
		# Update task with the difference (jiraWork - syncReported) Hours
		delta = jiraWork - syncReported

		print "      Reported to Rally %s hrs., to jira %s hrs. Delta %s hrs." % (syncReported, jiraWork, delta)

		print "  [@] Updating item %s: ACTUALS changed from [%s] to [%s], TODO changed from [%s] to [%s]" % (task.Id, task.Actuals, task.Actuals + delta, task.ToDo, task.ToDo - delta)
		task.Actuals += delta
		task.ToDo -= delta
		if task.ToDo < 0:
			task.ToDo = 0
		task.Notes = "Progress for %s (%s)" % (lastWorkingDay, datetime.datetime.now().strftime("%H:%M:%S"))
		task.Save(["Actuals", "ToDo", "Notes"])
	else:
		print "      Reported times match."


# Processes (progress/close) tasks and defects related to given user story
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
			if issue.IsClosed() and kind:
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

			action = "v"
			if task.IsCompleted():
				if not ji.IsClosed():
					ji.Connect(soap, jiraAuth)
					ji.Close()
					action = "x"
			else:
				if ji.IsClosed():
					task.Close()
					action = "X"

		print " [%s] %s (%s)" % (action, task, task.Status)

		if action != "+" and worklogs.has_key(task.Id) and task.RevisionHistory:
			# Checking worklogs
			#print "  jira worklog: %s sec." % worklogs[task.Id]
			history = rf.GetRevisionHistory(task.RevisionHistory)
			UpdateProgressFor(task, history, worklogs[task.Id])


	
###################################################################################################################


lastWorkingDay = lastWorkday.strftime("%Y-%m-%d")


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

currentIteration = None
for ref in iterations:
	if iterations[ref].Name == config["current_iteration"]:
		currentIteration = iterations[ref]
		break;
	
if not currentIteration:
	print "[!] Current iteration (%s) wasn't found in Rally!" % config["current_iteration"]
	exit(0);

stories = rf.AskForUserStories(currentIteration, True)

for us in stories:
	story = stories[us]
	parentIssueId = None
	action = " "
	if not jiraIssues.has_key(story.Id):
		# Create new user story
		jiraIssues[story.Id] = CreateJiraIssueFrom(story, "", "8", [versionId, backlogVersionId])
		action = "+"
	else:
		ji = jiraIssues[story.Id]
		if story.IsCompleted():
			action = "v"
			if not ji.IsClosed():
				ji.Connect(soap, jiraAuth)
				#ji.Close()
				action = "x"

	issue = jiraIssues[story.Id]
	parentIssueId = issue.key
	print "\n[%s] %s (%s) - %s" % (action, story, parentIssueId, story.Status)

###### Tasks ######################################################################################	
	ProcessTasksFor(story, issue, 1)

###### Defects ####################################################################################	
	ProcessTasksFor(story, issue, 0)


print "\nDone!"