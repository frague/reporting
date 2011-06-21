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
		return self.Status in ["COMPLETED", "ACCEPTED", "Completed", "Accepted", "Closed"]
	
	# Fills the instance from given xml representation
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

		self.Status = (self.SubnodeValue(node, "State") or self.SubnodeValue(node, "TaskStatus"))
		self.Description = self.SubnodeValue(node, "Description")
		self.RevisionHistory = self.SubnodeProp(node, "RevisionHistory", "ref")
		self.CreationDate = self.SubnodeValue(node, "CreationDate")
		if self.CreationDate:
			self.CreationDate = datetime.datetime.strptime(self.CreationDate, "%Y-%m-%dT%H:%M:%S.%fZ").date()

		self.User = self.SubnodeProp(node, "User", "refObjectName")

		self.Project = self.SubnodeProp(node, "Project", "ref")
		self.ProjectName = self.SubnodeProp(node, "Project", "refObjectName")

		self.Actuals = float(self.SubnodeValue(node, "Actuals") or "0")
		self.ToDo = float(self.SubnodeValue(node, "ToDo") or "0")

	# Fills the instance from given dictionary
	def FillFromDict(self, d):
		for key in d:
			setattr(self, key, d[key])

	# Creates xml from instance's properties by given fieldset
	def CreateXml(self, fields):
		doc = libxml2.newDoc("1.0")
		root = doc.newChild(None, self.Type, None)
		
		for field in fields:
			if field.find("@") >= 0:
				(field, prop) = field.split("@", 2)
				node = root.newChild(None, field, None)
				node.setNsProp(None, prop, str(getattr(self, field)))
			else:
				root.newChild(None, field, str(getattr(self, field)))
		return doc

	# Sends request to Rally API
	def RequestApi(self, url, xml=None):
		if xml:
			headers = {"Content-type": "text/xml"}
			request = urllib2.Request(url, str(xml), headers)
		else:
			request = urllib2.Request(url)

		text = urllib2.urlopen(request).read()
		return text
	
	# Re-requests instance data by ref
	def ReRequest(self):
		if not self.ref:
			return False
		doc = libxml2.parseDoc(self.RequestApi(self.ref))
		self.ParseFromXml(doc.children)

		return True
		
	# Saves the instance
	def Save(self, fields):
		if not self.ref or not self.Type:
			return False

		doc = self.CreateXml(fields)
		root = doc.children
		root.setNsProp(None, "ref", self.ref)
		
		return self.RequestApi(self.ref, doc)

	# Creates new instance in Rally with given fieldset
   	def Create(self, fields, base_url):
		if not self.Type:
			return False

		# Parsing the response
		text = self.RequestApi("%s%s/create" % (base_url, self.Type.lower()), self.CreateXml(fields))

		# Re-Reading resulting object
		doc = libxml2.parseDoc(text)
		node = doc.xpathNewContext().xpathEval("//CreateResult/Object")

		try:
			self.ref = node[0].prop("ref")
			return self.ReRequest()
		except:
			return False

	# Closes issue in Rally
	def Close(self, assignee = ""):
		if self.Type == "Task":
			# Task
			self.State = "Completed"
			fields = ["State"]
		else:
			if self.Type == "Defect":
				# Defect
				self.State = "Closed"
				self.ScheduleState = "Completed"
				fields = ["State", "ScheduleState"]
		   	else:
		   		# UserStory - Hierarchical Requirement
				self.TaskStatus = "COMPLETED"
				fields = ["TaskStatus"]

		self.ToDo = "0"
		fields.append("ToDo")

		if assignee:
			self.Owner = assignee
			fields.append("Owner@ref")

		self.Save(fields)
		self.Status = "Completed"

	# String representation
	def __repr__(self):
		return "[%s] %s" % (self.Id, self.Name)
		#return "[%s] %s (%s)" % (self.Id, self.Name, self.ref)




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
			print text
		return text
	

	def BaseAsk(self, entity, query, fetch = False, debug = False):
		url = "%s%s?fetch=%s&query=(%s)" % (config["rally"]["rest"], entity, str(fetch).lower(), urllib.quote(query))
		return self.RequestXml(entity, url, debug)
		
	# Asking for specific types of objects
	def AskFor(self, entity, query, fetch = False, debug = False):
		text = self.BaseAsk(entity, query, fetch, debug)
		return self.ParseObjects(entity, text)


	def AskForIterations(self, project, fetch = False):
		return self.AskFor("Iteration", "Project.Name = \"%s\"" % (project), fetch)

	def AskForUserStories(self, iteration, project, fetch = False):
		return self.AskFor("HierarchicalRequirement", "(Iteration = \"%s\") AND (Project.Name = \"%s\")" % (iteration.ref, project), fetch)

	def AskForUserStoryTasks(self, user_story, fetch = False):
		return self.AskFor("Task", "WorkProduct = \"%s\"" % (user_story.ref), fetch)

	def AskForUserStoryDefects(self, user_story, fetch = False):
		return self.AskFor("Defect", "Requirement = \"%s\"" % (user_story.ref), fetch)

	def AskForStandaloneDefects(self, iteration, project, fetch = False):
		return self.AskFor("Defect", "((Iteration = \"%s\") AND (Project.Name = \"%s\")) AND (Requirement = \"\")" % (iteration.ref, project), fetch)

	def AskForUser(self, name, fetch = False):
		text = self.BaseAsk("User", "DisplayName = \"%s\"" % name, fetch)
		users = self.ParseObjectsBase("User", "//QueryResult/Results/Object[@type='User']", text)
		if users:
			return users[users.keys()[0]]
		return False

	def GetRevisionHistory(self, ref):
		text = self.RequestXml("Revision", ref)
		return self.ParseObjectsBase("Revision", "//RevisionHistory/Revisions/Revision[@type='Revision']", text)

	# Gets User ref by short name (ivasilyev) and caches it
	usersRefs = {}
	def GetUserRef(self, name):
		global config

		if self.usersRefs.has_key(name):
			return self.usersRefs[name]

		if not name:
			return name
		
		user = self.AskForUser(config["logins_names"][name])
		if user:
			self.usersRefs[name] = user.ref
			return user.ref
		return ""

	# Creates Rally item from jira issue
	jiraTypes = {"5": "Task", "1": "Defect", "8": "HierarchicalRequirement"}
	def CreateRallyIssueFrom(self, jira_issue, project, iteration, parent = ""):
		result = RallyObject()
		try:
			result.Type = self.jiraTypes[jira_issue.type]
		except:
			result.Type = self.jiraTypes[jira_issue.issuetype]

		result.Name = jira_issue.summary
		result.Description = jira_issue.description

		result.Owner = self.GetUserRef(jira_issue.assignee)

		result.Project = project
		result.Iteration = iteration
		result.WorkProduct = parent

		result.Estimate = str(jira_issue.original_estimate) or "8"
		result.ToDo = str(jira_issue.remaining_estimate) or "8"
		result.Actuals = str(jira_issue.time_spent) or "0"
	
		if result.Create(["Name", "Description", "Owner@ref", "Project@ref", "Iteration@ref", "WorkProduct@ref", "Estimate", "ToDo", "Actuals"], config["rally"]["rest"]):
			return result
		return False



# Reformats issue description
replaces = {"<b>": "*", "</b>": "*", "<br[^>]*>": "\n", "<div>": "\n"}
not_tags = {"&nbsp;": " ", "&lt;": "<", "&gt;": ">", "&amp;": "&", "\n+": "\n", "\s+\n": "\s\n"}
def ReformatDescription(text):
	for needle in replaces:
		text = re.sub(r"(?i)%s" % needle, replaces[needle], text)
	text = DeTag(text)
	for needle in not_tags:
		text = re.sub(r"(?i)%s" % needle, not_tags[needle], text)

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

		print "   | Reported to Rally %s hrs., to jira %s hrs. Delta %s hrs." % (syncReported, jiraWork, delta)

		print "   | Updating item %s: ACTUALS changed from [%s] to [%s], TODO changed from [%s] to [%s]" % (task.Id, task.Actuals, float(task.Actuals) + float(delta), task.ToDo, float(task.ToDo) - float(delta))
		task.Actuals += delta
		task.ToDo -= delta
		if task.ToDo < 0:
			task.ToDo = 0
		task.Notes = "Progress for %s (%s)" % (lastWorkingDay, datetime.datetime.now().strftime("%H:%M:%S"))
		task.State = "In-Progress"
		task.Save(["Actuals", "ToDo", "Notes", "State"])
	else:
		#print "      Reported times match."
		pass


# Processes (progress/close) tasks and defects related to given user story
def ProcessTasksFor(story, issue, kind):
	global versionId, backlogVersionId, parentIssueId, syncedIssues, soap, jiraAuth, worklogs, rf, currentIteration

	t = ""
	if kind == 0:
		t = "User Story Tasks"
		tasks = rf.AskForUserStoryTasks(story, True)
	elif kind == 1:
		t = "User Story Defects"
		tasks = rf.AskForUserStoryDefects(story, True)

	print "-- %s (%s):" % (t, len(tasks))

	for t in tasks:
		task = tasks[t]

		action = " "
		if not syncedIssues.has_key(task.Id):
			action = "+"
#			if issue.IsClosed() and kind:
			if issue.IsClosed():
				action = "/"
			else:
				if kind:
					i = CreateJiraIssueFrom(task, "", "1", [backlogVersionId])
				else:
					i = CreateJiraIssueFrom(task, parentIssueId, None, [versionId, backlogVersionId])

				if not i.key:
					action = "!"
		else:
			ji = syncedIssues[task.Id]
#			print "%s vs. %s"  % (task.IsCompleted(), ji.IsClosed())

			action = " "
			if task.IsCompleted():
				if not ji.IsClosed():
					ji.Connect(soap, jiraAuth)
					ji.Close()
					action = "x"
			else:
				if ji.IsClosed():
					task.Close(rf.GetUserRef(ji.assignee))
					action = "X"

		print " [%s] %s (%s)" % (action, str(task)[0:80], task.Status)

		if action != "+" and worklogs.has_key(task.Id) and task.RevisionHistory:
			# Checking worklogs
			#print "  jira worklog: %s sec." % worklogs[task.Id]
			history = rf.GetRevisionHistory(task.RevisionHistory)
			UpdateProgressFor(task, history, worklogs[task.Id])


	
###################################################################################################################


lastWorkingDay = lastWorkday.strftime("%Y-%m-%d")


ProfileNeeded()

subTasks = {}
syncedIssues = {}

print "--- Reading jira worklogs ----------------------------------"
worklogs = GetWorkLogs(lastWorkday, today, WorklogForRally)

print "\n--- Reading jira tasks -------------------------------------"

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


# Reading all User Stories from jira
for i in soap.getIssuesFromJqlSearch(jiraAuth, "project = \"%s\" AND ((issuetype = \"User Story\" AND fixVersion = \"%s\") OR issuetype = \"Bug\")" % (config["project_abbr"], config["current_version"]), 1000):
	issue = JiraIssue()
	issue.Parse(i)

	key = GetMatchGroup(issue.summary, rallyIssueExpr, 1)
	if key:
		syncedIssues[key] = issue
	
	# If not a bug
	if not issue.type == "1":
		# Gettings sub-tasks
		for j in soap.getIssuesFromJqlSearch(jiraAuth, "parent = \"%s\"" % issue.key, 50):
			sub_issue = JiraIssue()
			sub_issue.Parse(j)
			AppendSubSet(subTasks, issue.key, sub_issue)

			key = GetMatchGroup(sub_issue.summary, rallyIssueExpr, 1)
			if key:
				syncedIssues[key] = sub_issue


print "\n--- Reading jira tasks estimations -------------------------"
est = GetJiraIssuesEstimates(config["project_abbr"], config["current_version"])


print "\n--- Reading rally tasks ------------------------------------"

rf = RallyRESTFacade()

iterations = rf.AskForIterations(config["rally_project"], True)

currentIteration = None
for ref in iterations:
	if iterations[ref].Name == config["current_iteration"]:
		currentIteration = iterations[ref]
		break;
	
if not currentIteration:
	print "[!] Current iteration (%s) wasn't found in Rally!" % config["current_iteration"]
	exit(0);


stories = rf.AskForUserStories(currentIteration, config["rally_project"], True)
stories.update(rf.AskForStandaloneDefects(currentIteration, config["rally_project"], True))

#---------------- Main logic -------------------------

for us in stories:
	story = stories[us]
	parentIssueId = None
	action = " "

	# Checking if Rally User Story exists in jira
	if not syncedIssues.has_key(story.Id):
		# create new user story in jira if doesn't
		syncedIssues[story.Id] = CreateJiraIssueFrom(story, "", "8", [versionId, backlogVersionId])
		action = "+"
	else:
		ji = syncedIssues[story.Id]
		# or synchronize all subtasks created in jira to Rally
		if subTasks.has_key(ji.key):
			for st in subTasks[ji.key]:
				key = GetMatchGroup(st.summary, rallyIssueExpr, 1)
				if not key and not st.IsClosed():
					# Set original estimate
					if est.has_key(st.key):
						st.original_estimate = est[st.key]["Original"]
						st.remaining_estimate = est[st.key]["Remaining"]
						st.time_spent = est[st.key]["Spent"]

					ri = rf.CreateRallyIssueFrom(st, currentIteration.Project, currentIteration, story.ref)
					if ri and ri.Id:
						st.Connect(soap, jiraAuth)
						st.summary = "(%s) %s" % (ri.Id, st.summary)
						st.Update([{"id": "summary", "values": st.summary}])
						syncedIssues[ri.Id] = st

		# or close jira issue if it is closed in Rally
		if story.IsCompleted():
			action = "v"
			if not ji.IsClosed():
				ji.Connect(soap, jiraAuth)
				ji.Close()
				action = "x"

	issue = syncedIssues[story.Id]
	parentIssueId = issue.key
	print "\n[%s] %s (%s) - %s" % (action, story, parentIssueId, story.Status)

###### Tasks ######################################################################################	
	ProcessTasksFor(story, issue, 0)

###### Defects ####################################################################################	
	ProcessTasksFor(story, issue, 1)


print "\nDone!"
