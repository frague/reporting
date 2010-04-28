from rabbithole import *

class TestCase:
	empty = True
	Assignee = ""
	IsClosed = ""

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
			self.Description = deNewLine(self.Description)
			self.ExpectedResult = deNewLine(self.ExpectedResult)
			self.Comments = deNewLine(self.Comments)

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

	def Publish(self):
		GetJira({"action": "createIssue", "project": "TORS", "type": "Task", "fixVersions": "Code Hardening 2", "summary": "%s: %s" % (self.Number, self.Name), "description": "*Actions*: \\n %s \\n  \\n *Expected Result*: \\n %s \\n  \\n *Comments*: %s" % (self.Description, self.ExpectedResult, self.Comments), "priority": self.Priority})

	def ToTabSeparated(self):
		return "\t".join([self.Number, self.PRD, self.Name, self.Description, self.ExpectedResult, self.Priority, self.Status, self.Comments])


# ---------------------------------------------------------

multiline = re.compile('"([^"]+)"', re.MULTILINE)

def reNewLine(matchObj):
	return matchObj.group(1).replace("\n", "\\\\")

def deNewLine(text):
	return text.replace("\\\\", " \\n ").replace('"', "")

def cleanNewLines(text):
	text = text.replace("\\\\", " ")
	return re.sub(" +", " ", text)

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
	csv.append(task.ToTabSeparated())
	if justOne:
		justOne = False
		task.Publish()

WriteFile("csv/merged.txt", "\n".join(csv))