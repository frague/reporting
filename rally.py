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



###################################################################################################################

print "--- Reading jira tasks -------------------------------------"


print "--- Reading rally tasks ------------------------------------"



rf = RallyRESTFacade()
iterations = rf.AskForIterations("RAS")
stories = rf.AskForUserStories(iterations["Sprint 1 (2/7 - 2/18)"], True)

for us in stories:
	story = stories[us]
	print "[?] %s" % story
	tasks = rf.AskForUserStoryTasks(story, True)
	for task in tasks:
		print " [?] %s" % tasks[task]