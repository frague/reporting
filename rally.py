from rabbithole import *


class RallyObject():
	def __init__(self, node = None):
		if node:
			self.ParseFromXml(node)

	def ParseFromXml(self, node):
		self.ref = node.prop("ref")
		self.Name = node.prop("Name")
		self.Type = node.prop("Type")


class RallyRESTFacade():
	def __init__(self):
		pm = urllib2.HTTPPasswordMgrWithDefaultRealm()
		pm.add_password(None, config["rally"]["rest"], config["rally"]["user"], config["rally"]["password"])
		handler = urllib2.HTTPBasicAuthHandler(pm)

		opener = urllib2.build_opener(handler)
		urllib2.install_opener(opener)

	def ParseObjects(self, entity, text):
		doc = libxml2.parseDoc(text)
		return [RallyObject(q) for q in doc.xpathNewContext().xpathEval("//Results/Object[@type='%s']" % entity)]

	def AskFor(self, entity, query, fetch = False):
		request = urllib2.Request("%s%s?fetch=false&query=(%s)" % (config["rally"]["rest"], entity, urllib.quote(query)))
		return self.ParseObjects(entity, urllib2.urlopen(request).read())

	def AskForIterations(self, project, fetch = False):
		return self.AskFor("Iteration", "Project.Name = \"%s\"" % (project), fetch)

rf = RallyRESTFacade()
print rf.AskForIterations("RAS")

