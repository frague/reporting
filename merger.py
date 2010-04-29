from rabbithole import *

class TestCase:
	empty = True
	Assignee = ""
	IsClosed = ""
	jiraKey = ""

	def __init__(self, tabDelimited):
		columns = tabDelimited.split("\t")
		l = len(columns)
		if l == 8 or l == 10:
			try:
				# Old format (10 columns)
			   	(self.Number, self.PRD, self.Name, self.Description, self.ExpectedResult, self.Priority, self.Status, self.Comments, self.Assignee, self.IsClosed) = columns
			except:
				# New format (8 columns)
			   	(self.Number, self.PRD, self.Name, self.Description, self.ExpectedResult, self.Priority, self.Status, self.Comments) = columns

			self.Name = cleanNewLines(self.Name)
			if self.IsClosed:
				self.IsClosed = "Closed"

			if self.Priority and self.Number:
				self.empty = False
				self.Priority = makePriority(self.Priority)
		
	def IsEmpty(self):
		return self.empty
	
	def Print(self):
		print "+ %s: \"%s...\". %s (%s)" % (self.Number, self.Name[0:30], self.Assignee, self.IsClosed)

	def Equals(self, to):
		return self.Name == to.Name

	def Adopt(self, who):
		self.Assignee = who.Assignee
		self.IsClosed = who.IsClosed

	def Publish(self, project, version):
		result = GetJira({"action": "createIssue", "project": project, "type": "Task", "fixVersions": version, "summary": "%s: %s" % (self.Number, self.Name), "description": "*Actions*: \\n %s \\n  \\n *Expected Result*: \\n %s \\n  \\n *Comments*: %s \\n  \\n *PRD*: %s" % (deNewLine(self.Description), deNewLine(self.ExpectedResult), deNewLine(self.Comments), deNewLine(self.PRD)), "priority": self.Priority, "assignee": self.Assignee})
		self.jiraKey = re.sub("^.*(%s-[0-9]+).*$" % project, "\\1", result).strip()

		if self.IsClosed and self.jiraKey:
			GetJira({"action": "progressIssue", "issue": self.jiraKey, "step": 2})

	def ToTabSeparated(self):
		return "\t".join([self.Number, truNewLine(self.PRD), self.Name, truNewLine(self.Description), truNewLine(self.ExpectedResult), self.Priority, self.Status, truNewLine(self.Comments), self.Assignee, self.IsClosed])

	def ToXML(self):
		keys = ["Number", "PRD", "Summary", "Description", "ExpectedResult", "Priority", "Status", "Comments", "Assignee", "IsClosed"]
		pairs = {"Number": self.Number, "PRD": self.PRD, "Summary": self.Name, "Description": self.Description, "ExpectedResult": self.ExpectedResult, "Priority": self.Priority, "Status": self.Status, "Comments": self.Comments, "Assignee": self.Assignee, "IsClosed": self.IsClosed}
		return "<line>%s</line>" % "".join(["<%s>%s</%s>" % (key, deXml(truNewLine(pairs[key])), key) for key in keys])


# ---------------------------------------------------------

multiline = re.compile('"([^"]+)"', re.MULTILINE)

def reNewLine(matchObj):
	return matchObj.group(1).replace("\n", "\\\\")

def deNewLine(text):
	return text.replace("\\\\", " \\n ").replace('"', "")

def truNewLine(text):
	return text.replace("\\\\", "\n")

def cleanNewLines(text):
	text = text.replace("\\\\", " ")
	return re.sub(" +", " ", text)

def deXml(text):
	return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

def makePriority(p):
	if p == "P1":
		return "Critical"
	return "Major"

def readTasks(source):
	result = {}
	tasks = multiline.sub(reNewLine, ReadFile(source))
	for line in re.split("\n", tasks):
		task = TestCase(line)
		if task.IsEmpty():
			print "- Failed: line \"%s\", len %s" % (line, len(line.split("\t")))
		else:
			result[task.Name] = task
	print "%s tasks were loaded successfully." % len(result)
	return result


ProfileNeeded()


print "-- Reading both new and old tasks:"
old = readTasks("csv/old.txt")
new = readTasks("csv/new.txt")
result = {}
print "-- Searching for the intersections:"
for key in new.keys():
	if old.has_key(key):
		new[key].Adopt(old[key])
		print "-- Intersection of %s with %s" % (new[key].Number, old[key].Number)
	result[new[key].Number] = new[key]
print "-- Store results:"
csv = []
justOne = True
for key in sorted(result.iterkeys()):
	task = result[key]
	task.Print()
	csv.append(task.ToXML())
	task.Publish(config["project_abbr"], "Code Hardening 2")

WriteFile("csv/merged.xml", "<doc>%s</doc>" % "".join(csv))