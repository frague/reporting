import warnings
warnings.simplefilter("ignore", DeprecationWarning)

import os
import re
import sys
import yaml
import uuid
import urllib
import SOAPpy
import urllib
import getpass
import libxml2
import urllib2
import httplib2
import datetime
import xmlrpclib
import subprocess
from skype import *
from jabber import *
from datetime import timedelta


# File operations
def ReadFile(file_name):
	result = ""
	if os.path.exists(file_name):
		rf = file(file_name, "r")
		result = rf.read()
		rf.close()
	return result

def WriteFile(file_name, contents):
	wf = file(file_name, "w")
	wf.write(contents)
	wf.close()

# Reading config
config = yaml.load(ReadFile("conf/rabbithole.yaml"))

jiraAuth = None
soap = None

# Getting command-line parameters
param_expr = re.compile("^--([a-z]+)(=(.*)){0,1}$", re.IGNORECASE)
parameters = {}
for key in sys.argv:
	result = param_expr.match(key)
	if result:
		parameters[result.group(1)] = result.group(3) or True

def GetParameter(name):
	if parameters.has_key(name):
		return parameters[name]
	else:
		return ""


# Load profile if passed as parameter
profile = GetParameter("profile")
if profile != "":
	config.update(yaml.load(ReadFile("profiles/%s" % profile)))

dayOffs = config["day_offs"]

###################################################################
# Precompiled regexps

abbr = "JKHFKJHEKJHKJHKSDJDH"
if config.has_key("project_abbr"):
	abbr = config["project_abbr"]
project_issue = re.compile("\\\\{0,1}\[{0,1}%s-([0-9]+)\]{0,1} *" % abbr, re.IGNORECASE)
wiki_slashes = re.compile("([\[\{])")

isNumber = re.compile("^[0-9]+$")
reportLine = re.compile("^[^,]+(, [^,]+){8}$")
weekends = re.compile("(Sat|Sun)")
ignore_key = re.compile("^--ignore=", re.IGNORECASE)
regexpReserved = re.compile("([\[\]\{\}\.\?\*\+\-])")

today = datetime.date.today()
yesterday = today - timedelta(days = 1)
tomorrow = today + timedelta(days = 1)
lastWorkday = yesterday
while (weekends.match(lastWorkday.strftime("%a"))):
	lastWorkday = lastWorkday - timedelta(days = 1)

def deRegexp(text):
	return regexpReserved.sub("\\\\\\1", text)

def deHtml(text):
    return text.replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>').replace('&quot;', '"').replace('&#39;', "'")


# Creates RegExp for matching text until given word will be met
def NotEqualExpression(word):
	collector = ""
	result = ""
	for char in word:
		char = deRegexp(char)
		if result:
			result += "|"
		if collector:
			result += collector
		result += "[^%s]" % char
		collector += char
	return "(%s)" % result

# Searches haystack for expression, trying to return requested group string
# if not found - emty string will be returned
def GetMatchGroup(haystack, expr, group, default = ""):
	a = expr.search(haystack)
	if a:
		return a.group(group)
	return default


# Exits if no profile passed as parameter
def ProfileNeeded():
	if profile == "":
		exit("[!] Profile is not specified!")
	else:
		print "==== Profile: %s" % profile

# Checks if sub-set exists and adds new value to it
def AppendSubSet(set, key, value):
	if (set.has_key(key)):
		set[key].append(value)
	else:
		set[key] = [value]


# Read web page content
def GetWebPage(url, timeout = 60):
	website = urllib2.urlopen(url, timeout=timeout)
	website_html = website.read()
	website.close()
	return website_html


# Date methods
# Makes datetime object from set of its components
def DateFromSet(set):
	return datetime.datetime(set[0], set[1], set[2], set[3], set[4])

# Returns datetime object formatted for printing
def PrintableDate(date):
	return date.strftime("%B, %d (%A)")
	#return date.strftime("%d/%m/%Y %H:%M")

# Returns datetime object formatted for printing
def PrintableDateTime(date):
	return date.strftime("%Y-%m-%d, %H:%M")

# Formats date for charts
def MakeChartDate(date):
	return date.strftime("%Y/%m/%d")
	
# Making parameters line w/ login & password
def MakeParamsWithLogin(params, add_params):
	params.update(add_params)
	return MakeParams(params)

def FormatParam(value):
	result = value.replace("\"", "\\\"").replace("\n", "\\\\n")
	return result

# Making parameters line
def MakeParams(params):
	return " ".join('--%s "%s"' % (key, FormatParam(params[key])) for key in params.keys())

# Getting output of executable w/ parameters
def GetStdoutOf(process, params=""):
	p = subprocess.Popen("%s %s" % (process, params), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True).stdout
	return p.read()

# Getting single line from Jira or Wiki
def GetPage(page, params, add_params):
	params = MakeParamsWithLogin(params, add_params)
	#print "Params: %s" % params
	return GetStdoutOf(page, params)

def WgetPage(url):
	name = str(uuid.uuid1())
	os.system("wget %s -t1 -T120 -O %s" % (url, name))
	result = ReadFile(name)
	os.remove(name)
	return result

def GetWiki(add_params = {}):
	return GetPage("confluence.bat", config["wiki"], add_params)

def GetJira(add_params = {}):
	return GetPage("jira.bat", config["jira"], add_params)

def SaveWikiPage(wikiServer, wikiToken, space, title, content, parentPage = ""):
	try:
		page = wikiServer.confluence1.getPage(wikiToken, space, title)
		if parentPage:
			parent = wikiServer.confluence1.getPage(wikiToken, space, parentPage)
			page["parentId"] = parent["id"]
	except:
		page = {"space": space, "title": title}
	page["content"] = content
	return wikiServer.confluence1.storePage(wikiToken, page)

def SaveWikiNews(wikiServer, wikiToken, space, title, content):
	entry = {"space": space, "title": title, "content": content}
	return wikiServer.confluence1.storeBlogEntry(wikiToken, entry)

# Update cache file with received data
# Returns updated dictionary
def SaveUpdates(project, version_name, status):
	name = re.sub(" ", "", "cache/%s_%s.yaml" % (project, re.sub("[^a-zA-Z0-9]", "_", version_name)))
	existing = yaml.load(ReadFile(name)) or {}
	existing.update({datetime.date.today(): status})
	WriteFile(name, yaml.dump(existing))
	return existing
	
# Count jira issues of each status by given version
def CountJiraIssuesStatuses(project, version_name):
	global jiraAuth, soap

	if (jiraAuth == None):
		InitJiraSOAP()

	# Getting Issues by Jql filter
	status = {}
	for i in soap.getIssuesFromJqlSearch(jiraAuth, "project = '%s' AND fixVersion = '%s'" % (project, version_name), 1000):
		issue = JiraIssue()
		issue.Parse(i)

		if issue.type == "5":
			# Skip subtasks
			continue

		try:
			status_name = config["statuses"][int(issue.status)]
			if status_name == "To Be Reviewed" or status_name == "To Be Accepted":
				status_name = "Resolved"

			if status.has_key(status_name):
				status[status_name] += 1
			else:
				status[status_name] = 1
		except:
			pass		# Not standard status
	return status

def GetChild(source, name, attr):
	x = source.xpathEval(name)
	if len(x) > 0:
		return x[0].prop(attr)
	return ""

def NonEmptyFrom(v1, v2):
	if v1:
		return v1
	return v2



def GetJiraXmlByVersion(project, version_name):
	global config

	url = config["jira"]["server"] + "/sr/jira.issueviews:searchrequest-xml/temp/SearchRequest.xml?jqlQuery=project+%3D+" + config["project_abbr"] + "+AND+fixVersion+%3D+%22" + urllib.quote(version_name) + "%22+ORDER+BY+updated+DESC%2C+priority+DESC%2C+created+ASC&tempMax=1000&os_username=" + config["jira"]["user"] + "&os_password=" + config["jira"]["password"]

	http = httplib2.Http()
	headers = {}
	response, content = http.request(url, 'GET', headers=headers)

	doc = libxml2.parseDoc(content)
	return doc.getRootElement()


def GetJiraIssuesEstimates(project, version_name):
	global config

	root = GetJiraXmlByVersion(project, version_name)
	result = {}

	for item in root.xpathEval("//item"):
		type = item.xpathEval("type")[0].content

		key = item.xpathEval("key")[0].content
		status = item.xpathEval("status")[0].content

		original = NonEmptyFrom(GetChild(item, "aggregatetimeoriginalestimate", "seconds"), GetChild(item, "timeoriginalestimate", "seconds"))
		remaining = NonEmptyFrom(GetChild(item, "aggregatetimeremainingestimate", "seconds"), GetChild(item, "timeestimate", "seconds"))
		
		if status == "Closed" or status == "Resolved":
			remaining = "0"

		totalOriginal = 0.0
		totalRemaining = 0.0

		try:
			totalOriginal = float(original)
			totalRemaining = float(remaining)
		except:
			pass

		result[key] = {"Original": totalOriginal / 3600, "Remaining": totalRemaining / 3600, "Spent": (totalOriginal - totalRemaining) / 3600}

	return result
	


def CountJiraIssuesEstimates(project, version_name):
	global config

	root = GetJiraXmlByVersion(project, version_name)

	originalEstimate = {}
	remainEstimate = {}

	totalOriginal = 0.0
	totalRemaining = 0.0

	for item in root.xpathEval("//item"):
		type = item.xpathEval("type")[0].content

		if (type == "Sub-Task"):
			continue

		key = item.xpathEval("key")[0].content
		title = item.xpathEval("title")[0].content
		status = item.xpathEval("status")[0].content

		original = NonEmptyFrom(GetChild(item, "aggregatetimeoriginalestimate", "seconds"), GetChild(item, "timeoriginalestimate", "seconds"))
		remaining = NonEmptyFrom(GetChild(item, "aggregatetimeremainingestimate", "seconds"), GetChild(item, "timeestimate", "seconds"))
		
		if status == "Closed" or status == "Resolved":
			remaining = "0"

		try:
			totalOriginal += float(original)
			totalRemaining += float(remaining)
		except:
			pass

#	print "[%s] Original=%s, Spent=%s, Remaining=%s" % (key, totalOriginal, totalSpent, totalRemaining)

#	doc.freeDoc()

	# Jira day = 8 hours (28800 seconds) !!!
	return {"Original": totalOriginal / 28800, "Remaining": totalRemaining / 28800, "Spent": (totalOriginal - totalRemaining) / 28800}


# Reads template from filesystem
def GetTemplate(template_name):
	return ReadFile("templates/%s" % template_name)

# Fills template by values from given dictionary
def FillTemplate(template, values):
	for chunk in values.keys():
		template = template.replace(chunk, values[chunk])
	return template

# Retrieves data from jira by project and version name and appends storage file with it
def GetAndSaveJiraVersionIssues(project, version_name):
	status = CountJiraIssuesStatuses(project, version_name)
	return SaveUpdates(project, version_name, status)

# Retrieves data from jira by project and version name and appends storage file with it
def GetAndSaveJiraVersionTimings(project, version_name):
	status = CountJiraIssuesEstimates(project, version_name)
	return SaveUpdates(project, version_name + "_timing", status)

# Makes Wiki-syntax bar-chart markup for given data
def MakeWikiBarChart(data, name=""):
	print " * Create chart %s - %s line(s)" % (name, len(data))
	dates = data.keys()
	dates.sort()
	result = "|| || %s ||" % " || ".join(MakeChartDate(date) for date in dates)
	for status in config["statuses_order"]:
	 	result += "\n| %s | " % status
	 	for date in dates:
	 		if data[date].has_key(status):
	 			result += " %s |" % data[date][status]
		 	else:
		 		result += " 0 |"
	return result

# Makes ideal burndown straight guideline
def MakeWikiStraightLine(data, max_value, deadline):
	min_date = min([date for date in data.keys()])

	date = min_date
	flat = {};
	while (date <= deadline):
		if date not in dayOffs and (not weekends.match(date.strftime("%a")) or date == deadline or data.has_key(date)):
			flat[date] = True
		date = date + timedelta(days = 1)

	max_days = len(flat) - 1
	result = ""
	dates = flat.keys()
	dates.sort()
	i = 0
	for date in dates:
		level = max_value
		if max_days > 0:
			level = ((max_days - i - 0.0)/max_days) * max_value

		result += "| %s | %s |\n" % (MakeChartDate(date), level)
		i += 1
	return result

# Makes Wiki-syntax line (point) burndown markup for given data
def MakeWikiBurndownLine(data, statuses, initial_level, statuses_to_calc_total = []):
	result = ""
	dates = data.keys()
	dates.sort()
	i = 0
	for date in dates:
		if date in dayOffs:
			continue

		level = initial_level

		max_delta = 0
#		if len(statuses_to_calc_total) > 0:
#			level = initial_level - sum([int(data[date][s]) for s in statuses_to_calc_total])

		for status in statuses:
			if data[date].has_key(status):
				if initial_level > 0:
					level -= int(data[date][status])
				else:
					level += int(data[date][status])

		level -= max_delta
		result += "| %s | %s |\n" % (MakeChartDate(date), level)
		i += 1
	return result

# Makes Wiki-syntax burndown markup for given data
def MakeWikiBurndownChart(data, deadline, name=""):
	print " * Create chart %s - %s line(s)" % (name, len(data))

	max_tasks = max([sum(data[date].values()) for date in data.keys()])

	result = "|| Day || Guideline ||\n"
	result += MakeWikiStraightLine(data, max_tasks, deadline)
	result += "\n|| Day || Burndown chart ||\n"
	result += MakeWikiBurndownLine(data, ["Closed", "Resolved"], max_tasks)

	return result
	
# Makes Wiki-syntax burndown markup for given data
def MakeWikiTimingChart(data, deadline, name=""):
	print " * Create timing chart %s - %s line(s)" % (name, len(data))

	max_length = max([data[date]["Original"] for date in data.keys()])

	result = "|| Day || Guideline ||\n"
	result += MakeWikiStraightLine(data, max_length, deadline)
	result += "\n|| Day || Burndown chart ||\n"
	result += MakeWikiBurndownLine(data, ["Spent"], max_length, ["Original"])

	return result
	
# Makes Wiki-progress chart
def MakeWikiProgressChart(data, postfix="", order=[], maxPoints=40):
	print " * Create progress chart (%s line(s))" % len(data)
	dates = data.keys()
	dates.sort()
	result = ""
	
	if len(data) == 0:
		return result

	areas = order or data[data.keys()[0]].keys()

	for area in areas:
		result += "\n\n|| Day || %s ||" % area
	 	for date in dates[-maxPoints:]:
	 		result += "\n| %s " % MakeChartDate(date)
	 		if data[date].has_key(area):
	 			result += "| %s |" % data[date][area]
		 	else:
	 			result += "| 0 |"

	result += postfix
	
	return result



def WikiSlash(text):
	return wiki_slashes.sub("\\\\\\1", text)


#####################################################################################
# GIT Logs

def AddCommit(line, commits, lastWorkingDay):
	l = line.split("|")
	if (len(l) != 4):
		return

	[commitDate, email, commit, authorDate] = l
#	print "%s - %s" % (commitDate[:10], authorDate[:10])
	if (authorDate[:10] != lastWorkingDay):
		return

	commit = project_issue.sub("[%s-\\1@issues] " % config["project_abbr"], WikiSlash(commit))
	AppendSubSet(commits, email, commit)
	print " + %s: %s" % (email, commit)

def BindLogs(key, source, title):
	co = ""
	if source.has_key(key):
		co = "\n-- ".join([item for item in source[key]])

	if len(co) > 0:
		co = "\n*%s:*\n-- %s" % (title, co)
	return co


def BindTeamLogs(team_name, teams, commits, worklog, personTemplate):
	result = "h2. %s Team\n{section}\n{column:width=49%%}\n" % team_name
	i = 1
	divide = True
	for user in teams[team_name]:
		half = (len(teams[team_name]) / 2)

		# Adding commits
		co = BindLogs(config["emails"][user], commits, "git commits")

		# Adding worklogs
		wl = BindLogs(user, worklog, "jira worklogs")

		result += FillTemplate(personTemplate, {"##PERSON##": user, "##PREVIOUS##": "", "##TODAY##": "", "##COMMITS##": co, "##WORKLOGS##": wl})
		if divide and i >= half:
			result += "\n{column}\n{column:width=2%}\n"
			result += "\n{column}\n{column:width=49%}\n"
			divide = False
		i += 1

	result += "\n{column}\n{section}\n"
	return result

#####################################################################################
# Jira Worklogs

def InitJiraSOAP():
	global soap, jiraAuth

	soap = SOAPpy.WSDL.Proxy(config["jira_soap"])
	jiraAuth = soap.login(config["jira"]["user"], config["jira"]["password"])


rallyIssueExpr = re.compile("^\(((US|TA|DE)\d+)\) ")

def WorklogForRally(collector, issueTitle, issue):
	# We can potentially separate by author
	key = GetMatchGroup(issueTitle, rallyIssueExpr, 1)
	if key:
		if collector.has_key(key):
			collector[key] += issue["timeSpentInSeconds"]
		else:
			collector[key] = issue["timeSpentInSeconds"]
		print " + %s (%s sec.)" % (issue["timeSpent"], issue["timeSpentInSeconds"])


def GetWorkLogs(fromDate, tillDate, collectMethod = None):
	global soap, jiraAuth

	#found = {}

	if (jiraAuth == None):
		InitJiraSOAP()

	# Getting Issues by Jql filter
	updatedIssues = {}
	issues = soap.getIssuesFromJqlSearch(jiraAuth, "project = '%s' AND updatedDate >= '%s 00:00' ORDER BY updated DESC" % (config["project_abbr"], fromDate.strftime("%Y/%m/%d")), 100)
	for i in issues:
		updatedIssues[i["key"]] = i["summary"]

	worklogs = {}
	for issueKey in updatedIssues.keys():
		print "%s: \"%s\":" % (issueKey, updatedIssues[issueKey][0:80])
		issues = soap.getWorklogs(jiraAuth, issueKey)
		for i in issues:
			# + 3 hours for England
			comment = i["comment"] or ""
			startDate = DateFromSet(i["startDate"]) + timedelta(hours = 3)
			if startDate.date() >= fromDate and startDate.date() < tillDate:
				if collectMethod:
					collectMethod(worklogs, updatedIssues[issueKey], i)
				else:
					value = "[%s@issues] (%s) %s - %s" % (issueKey, WikiSlash(updatedIssues[issueKey]), WikiSlash(comment.strip(" \n\r")), i["timeSpent"])
					AppendSubSet(worklogs, i["author"], value)
					print " [+] %s: %s (%s)" % (i["author"], comment.strip(" \n\r"), i["timeSpent"])

				#found[i["author"]] = True

	return worklogs


#####################################################################################
# Worklog notifications

def RequestWorklogs(fromDate, worklogs, notifiee, engine, commits, ignore = []):
	global config 

	if (len(notifiee) > 0):

		notification = GetTemplate("notification")
		date = PrintableDate(fromDate)

		#print commits

		print "\nSending %s notifications about missing jira worklogs for %s:" % (engine.Name, date)

		for login in notifiee.keys():
			if not login in ignore:
				email = config["emails"][login]
				if not worklogs.has_key(login):
					commit = "None"
					if commits.has_key(email):
						commit = "\n- " + "\n- ".join(commits[email])

					print " [+] %s" % login
					engine.SendMessage(notifiee[login], FillTemplate(notification, {"##DATE##": date, "##COMMITS##": commit, "##SPRINT##": config["currentSprint"]}))
			else:
				print " [-] %s (ignored)" % login

		engine.Disconnect()

######################################################################################
# Jira Issue class

class JiraIssue:
	global config

	def __init__(self):
		self.IsConnected = False
		self.Clear()
		pass

	def Connect(self, soap, jiraAuth):
		self.soap = soap
		self.jiraAuth = jiraAuth
		self.IsConnected = True
		pass

	def Number(self):
		if self.IsNotEmpty():
			return int(re.sub("[^0-9]", "", self.key))
		else:
			return 0

	def Parse(self, line):
		self.Clear()
		for key in line._keys():
			setattr(self, key, line[key] or "")
		if self.type:
			self.issuetype = self.type

	
	def Clear(self):
		self.id = 0
		self.key = ""
		self.summary = ""
		self.status = "1"
		self.description = ""
		self.priority = "3"
		self.type = ""
		self.issuetype = "3"
		self.assignee = ""
		self.reporter = ""
		self.fixVersions = []
		self.resolution = "-1"
		self.parentIssueId = ""
		self.original_estimate = "8"
		self.remaining_estimate = "8"
		self.time_spent = "0"

	def IsNotEmpty(self):
		return self.key and self.id

	def IsClosed(self):
		return self.IsNotEmpty() and (self.status == "5" or self.status == "6")

	def AssertEqual(self, a, b, msg):
#		if a != b:
#			print "%s: \"%s\" <> \"%s\"" % (msg, a, b)
		return a == b

	def MakeCodeSections(self, type = ""):
		if type:
			type = ":" + type

		self.description = re.sub("([^>])(\n<)", ("\\1{code%s}\\2" % type), self.description)
		self.description = re.sub("(>\n)([ \t\n]*[^< \t\n])", "\\1{code}\\2", self.description)
		if self.description.count("{code") % 2 != 0:
			self.description += "{code"
	
	def Equals(self, issue):
		result = True
		result = result and self.AssertEqual(self.key, issue.key, "Key")
		result = result and self.AssertEqual(self.issuetype, issue.issuetype, "Issue Type")
		result = result and self.AssertEqual(self.summary, issue.summary, "Summary")
		result = result and self.AssertEqual(self.description, issue.description, "Description")
		result = result and self.AssertEqual(self.priority, issue.priority, "Priority")
		result = result and self.AssertEqual(self.assignee, issue.assignee, "Assignee")
		return result
#		return self.key == issue.key and self.summary == issue.summary and self.description == issue.description and self.priority == issue.priority and self.assignee == issue.assignee

	def ToString(self, crop):
		return "[%s] %s (%s)" % (self.key or "...", self.summary[0:crop], self.priority)
	
	def ToStringFull(self, crop):
		return "[%s] %s (%s)\n%s" % (self.key or "...", self.summary[0:crop], self.priority, self.description)
	
	def Fetch(self, key = ""):
		if key:
			self.key = key
		if self.key and self.IsConnected:
			self.Parse(self.soap.getIssue(self.jiraAuth, self.key))
	
	def Create(self):
		if self.IsConnected:
#			newIssue = self.soap.createIssue(self.jiraAuth, {"project": self.project, "issuetype": self.issuetype, "priority": self.priority, "summary": self.summary, "description": self.description, "assignee": self.assignee, "reporter": self.reporter})
			newIssue = self.soap.createIssue(self.jiraAuth, {"project": self.project, "type": self.issuetype, "priority": self.priority, "summary": self.summary, "description": self.description, "reporter": self.reporter, "assignee": self.assignee})
			self.key = newIssue.key
			self.id = newIssue.id

	def CreateSubtask(self, parent_key):
		# Subtask creation available through CLI only (((
		if parent_key:
   			WriteFile("new_subtask.tmp", self.description)
			output = GetJira({"action": "createIssue", "project": self.project, "type": "Sub-task", "priority": self.priority, "summary": self.summary, "file": "new_subtask.tmp", "reporter": self.reporter, "assignee": self.assignee, "parent": parent_key})
			os.remove("new_subtask.tmp")

			#print "   Creation output: %s" % output
			self.key = GetMatchGroup(output, re.compile("^Issue ([A-Z0-9]+-\d+) created as subtask of"), 1)
			
	def Update(self, changes):
		if self.IsNotEmpty() and self.IsConnected:
			try:
				self.soap.updateIssue(self.jiraAuth, self.key, changes)
			except:
				print "[!] Error updating issue %s" % self.key

	def UpdateFrom(self, issue):
		if self.IsNotEmpty() and self.IsConnected:
			self.soap.updateIssue(self.jiraAuth, self.key, [{"id": "issuetype", "values": [issue.issuetype]}, {"id": "priority", "values": [issue.priority]}, {"id": "summary", "values": [issue.summary]}, {"id": "description", "values": [issue.description]}, {"id": "assignee", "values": [issue.assignee]}])

	def SetVersion(self, version):
		if self.IsNotEmpty() and self.IsConnected:
			self.Update([{"id": "fixVersions", "values": version}])

	def Resolve(self):
		if self.IsNotEmpty() and self.IsConnected:
			self.soap.progressWorkflowAction(self.jiraAuth, self.key, '2', [{"id": "resolution", "values": "2"}])

	def Close(self):
		if self.IsNotEmpty() and self.IsConnected:
			action = "2"
			if self.status == "10078":
				# For "To Be Reviewed" and "To Be Accepted" statuses there is custom Close action
				action = "761"
			else:
				if self.status == "10068":
					# For "To Be Reviewed" and "To Be Accepted" statuses there is custom Close action
					action = "721"

			self.soap.progressWorkflowAction(self.jiraAuth, self.key, action, [{"id": "resolution", "values": "1"}])

	def Delete(self):
		if self.IsNotEmpty() and self.IsConnected:
			self.soap.deleteIssue(self.jiraAuth, self.key)

######################################################################################
# Text transforming methods

tagExpr = re.compile("<[^<]+>")
def DeTag(text):
	return tagExpr.sub("", text)

# Parses table with header into a set of dectionaries, one per each row
def ParseHeadedTable(markup, de_tag = False):
	markup = re.sub("</{0,1}tbody>", "", markup)	

	cols = []
	result = []
	isHeader = False
	for row in markup.strip().split("<tr>"):
		if not row:
			continue
		values = re.split("</t[dh]>", re.sub("</t[dh]>$", "", re.sub("<(/tr|td|th)>", "", row).strip()))
		if de_tag:
			values = [DeTag(i).strip() for i in values]

		if not isHeader:
			cols = values
			isHeader = True
		else:
			item = {}
			for i in range(len(cols)):
#				if cols[i] in ["Priority", "Total", "Low Priority", "Normal Priority", "High Priority"]:
				if cols[i] in ["Priority"]:
					values[i] = long(values[i])
				item[cols[i]] = values[i]
			result.append(item)
	return result
				

cellExpression = re.compile("(<t[rdh])[^>]*>", re.IGNORECASE)
def CleanHtmlTable(markup):
	return cellExpression.sub("\\1>", markup)

