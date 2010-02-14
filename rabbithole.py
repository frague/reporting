import os
import re
import sys
import yaml
import urllib
import datetime
import subprocess
from datetime import timedelta
import SOAPpy, getpass, datetime
	
statuses = ["", "Open", "", "In progress", "Reopened", "Resolved", "Closed"]
statuses_order = ["Closed", "Resolved", "In progress", "Reopened", "Open" ]

isNumber = re.compile("^[0-9]+$")
reportLine = re.compile("^[^,]+(, [^,]+){8}$")
weekends = re.compile("(Sat|Sun)")
tors = re.compile("\[{0,1}TORS-([0-9]+)\]{0,1} *", re.IGNORECASE)

jiraAuth = None

today = datetime.date.today()
yesterday = today - timedelta(days = 1)
lastWorkday = yesterday
while (weekends.match(lastWorkday.strftime("%a"))):
	lastWorkday = lastWorkday - timedelta(days = 1)

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

# Making parameters line w/ login & password
def MakeParamsWithLogin(add_params):
	args = yaml.load(ReadFile("conf/rabbithole.yaml"))
	args.update(add_params)
	return MakeParams(args)

# Making parameters line
def MakeParams(params):
	return " ".join('--%s "%s"' % (key, params[key]) for key in params.keys())

# Getting output of executable w/ parameters
def GetStdoutOf(process, params):
	p = subprocess.Popen("%s %s" % (process, params), stdout=subprocess.PIPE, shell=False).stdout
	return p.read()

# Getting single line from Jira or Wiki
def GetPage(page, add_params):
	return GetStdoutOf(page, MakeParamsWithLogin(add_params))

def GetWiki(add_params = {}):
	add_params["server"] = "https://wiki.griddynamics.net"
	return GetPage("confluence.bat", add_params)

def GetJira(add_params = {}):
	add_params["server"] = "https://issues.griddynamics.net"
	return GetPage("jira.bat", add_params)

# Update cache file with received data
# Returns updated dictionary
def SaveUpdates(filter_name, status):
	name = "conf/" + filter_name + ".status"
	existing = yaml.load(ReadFile(name)) or {}
	existing.update({datetime.date.today(): status})
	WriteFile(name, yaml.dump(existing))
	return existing
	
# Requests data from Jira by given filter name
def GetJiraFilterData(filter_name):
	status = {}
	for line in filter(lambda line: reportLine.match(line), GetJira({"action": "getIssueList", "filter": filter_name}).split("\n")):
		[Key, Id, Project, CurrentStatus, Priority, Assignee, Reporter, Created, DateDue] = line.split(", ")
		if isNumber.match(CurrentStatus):
			try:
				status[statuses[int(CurrentStatus)]] += 1
			except:
				status[statuses[int(CurrentStatus)]] = 1
	return status
		


def GetTemplate(template_name):
	return ReadFile("conf/%s.template"%template_name)

def FillTemplate(template, values):
	for chunk in values.keys():
		template = template.replace(chunk, values[chunk])
	return template

def GetAndSaveJiraFilteredData(filter_name):
	status = GetJiraFilterData(filter_name)
	return SaveUpdates(filter_name, status)

# Makes Wiki-syntax bar-chart markup for given data
def MakeWikiBarChart(data):
	dates = data.keys()
	dates.sort()
	result = "|| || %s ||" % " || ".join(date.strftime("%d/%m") for date in dates)
	for status in statuses_order:
	 	result += "\n| %s | " % status
	 	for date in dates:
	 		if data[date].has_key(status):
	 			result += " %s |" % data[date][status]
		 	else:
		 		result += " 0 |"
	return result

# Makes Wiki-syntax burndown markup for given data
def MakeWikiBurndownLine(data, max_tasks, max_days=0):
	max_days -= 1
	result = ""
	dates = data.keys()
	dates.sort()
	i = 0
	for date in dates:
		level = max_tasks
		if data[date].has_key("Closed"):
			if max_days > 0:
				level = ((max_days - i - 0.0)/max_days) * max_tasks
			else:
				level -= int(data[date]["Closed"])
		if data[date].has_key("Resolved"):
			level -= int(data[date]["Resolved"])

		result += "| %s | %s |\n" % (date.strftime("%d/%m"), level)
		i += 1
	return result

# Makes Wiki-syntax burndown markup for given data
def MakeWikiBurndownChart(data, deadline):
	max_tasks = max([sum(data[date].values()) for date in data.keys()])
	min_date = min([date for date in data.keys()])

	date = min_date
	flat = {};
	days = 0;
	while (date <= deadline):
		if (not weekends.match(date.strftime("%a")) or date == deadline):
			flat[date] = {"Closed": 0}
			days += 1
		date = date + timedelta(days = 1)

	result = "|| Day || Guideline ||\n"
	result += MakeWikiBurndownLine(flat, max_tasks, days)
	result += "\n|| Day || Burndown chart ||\n"
	result += MakeWikiBurndownLine(data, max_tasks)

	return result
	
#####################################################################################
# GIT Logs

def AddCommit(line, commits):
	l = line.split("|")
	if (len(l) != 4):
		return

	[commitDate, email, commit, authorDate] = l
#	print "%s - %s" % (commitDate[:10], authorDate[:10])
	if (commitDate[:10] != authorDate[:10]):
		return

	commit = tors.sub("[TORS-\\1@issues] ", commit)

	if (commits.has_key(email)):
		commits[email].append(commit)
	else:
		commits[email] = [commit]

	print " - %s: %s" % (email, commit)

def BindLogs(key, source, title):
	co = ""
	if source.has_key(key):
		co = "-- " + "\n-- ".join([item for item in source[key]])

	if len(co) > 0:
		co = "*%s*\n%s" % (title, co)
	return co


def BindTeamLogs(team_name, teams, commits, worklog, personTemplate):
	result = "h3. %s Team\n{section}\n{column:width=50%%}\n" % team_name
	i = 1
	divide = True
	for email in teams[team_name]:
		half = (len(teams[team_name]) / 2)

		# Adding commits
		co = BindLogs(email, commits, "Commits")

		# Adding worklogs
		wl = BindLogs(teams[team_name][email], worklog, "jira worklogs")

		result += FillTemplate(personTemplate, {"##PERSON##": teams[team_name][email], "##PREVIOUS##": "", "##TODAY##": "", "##COMMITS##": co, "##WORKLOGS##": wl})
		if divide and i >= half:
			result += "\n{column}\n{column:width=50%}\n"
			divide = False
		i += 1

	result += "\n{column}\n{section}\n"
	return result

#####################################################################################
# Jira Worklogs

def InitJiraSOAP():
	global soap, jiraAuth

	soap = SOAPpy.WSDL.Proxy('https://issues.griddynamics.net/rpc/soap/jirasoapservice-v2?wsdl')
 
	args = yaml.load(ReadFile("conf/rabbithole.yaml"))
	jirauser = args["user"]
	passwd = args["password"]

	jiraAuth = soap.login(jirauser, passwd)


def AppendSubSet(set, key, value):
	if (set.has_key(key)):
		set[key].append(value)
	else:
		set[key] = [value]

def DateFromSet(set):
	return datetime.date(set[0], set[1], set[2])
	
def GetWorkLogs(fromDate, tillDate):
	global soap, jiraAuth

	if (jiraAuth == None):
		InitJiraSOAP()

	## Getting Issues by Jql filter
	updatedIssues = {}
	issues = soap.getIssuesFromJqlSearch(jiraAuth, "project = TORS AND updatedDate >= '%s 00:00' ORDER BY updated DESC" % fromDate.strftime("%Y/%m/%d"), 100)
	for i in issues:
		updatedIssues[i["key"]] = i["summary"]

	workLogs = {}
	for issueKey in updatedIssues.keys():
		print "%s: \"%s\":" % (issueKey, updatedIssues[issueKey])
		issues = soap.getWorklogs(jiraAuth, issueKey)
		for i in issues:
			startDate = DateFromSet(i["startDate"])
			if startDate >= fromDate and startDate < tillDate:
				value = "[%s: %s|%s@issues] %s (%s)" % (issueKey, updatedIssues[issueKey], issueKey, i["comment"], i["timeSpent"])
#				value = "[%s|%s@issues] %s (%s)" % (issueKey, issueKey, i["comment"], i["timeSpent"])
				AppendSubSet(workLogs, i["author"], value)
				print " - %s: %s (%s)" % (i["author"], i["comment"], i["timeSpent"])

	return workLogs
