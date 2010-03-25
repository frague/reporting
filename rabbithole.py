import warnings
warnings.simplefilter("ignore", DeprecationWarning)

import os
import re
import sys
import yaml
import urllib
import SOAPpy
import getpass
import datetime
import subprocess
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

isNumber = re.compile("^[0-9]+$")
reportLine = re.compile("^[^,]+(, [^,]+){8}$")
weekends = re.compile("(Sat|Sun)")
project_issue = re.compile("\[{0,1}%s-([0-9]+)\]{0,1} *" % config["project_abbr"], re.IGNORECASE)

jiraAuth = None

today = datetime.date.today()
yesterday = today - timedelta(days = 1)
lastWorkday = yesterday
while (weekends.match(lastWorkday.strftime("%a"))):
	lastWorkday = lastWorkday - timedelta(days = 1)



# Checks if sub-set exists and adds new value to it
def AppendSubSet(set, key, value):
	if (set.has_key(key)):
		set[key].append(value)
	else:
		set[key] = [value]

# Date methods
# Makes datetime object from set of its components
def DateFromSet(set):
	return datetime.datetime(set[0], set[1], set[2], set[3], set[4])

# Returns datetime object formatted for printing
def PrintableDate(date):
	return date.strftime("%d/%m/%Y %H:%M")
	
# Making parameters line w/ login & password
def MakeParamsWithLogin(params, add_params):
	params.update(add_params)
	return MakeParams(params)

# Making parameters line
def MakeParams(params):
	return " ".join('--%s "%s"' % (key, params[key]) for key in params.keys())

# Getting output of executable w/ parameters
def GetStdoutOf(process, params):
	p = subprocess.Popen("%s %s" % (process, params), stdout=subprocess.PIPE, shell=False).stdout
	return p.read()

# Getting single line from Jira or Wiki
def GetPage(page, params, add_params):
	return GetStdoutOf(page, MakeParamsWithLogin(params, add_params))

def GetWiki(add_params = {}):
	return GetPage("confluence.bat", config["wiki"], add_params)

def GetJira(add_params = {}):
	return GetPage("jira.bat", config["jira"], add_params)

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
				status[config["statuses"][int(CurrentStatus)]] += 1
			except:
				status[config["statuses"][int(CurrentStatus)]] = 1
	return status
		

# Reads template from filesystem
def GetTemplate(template_name):
	return ReadFile("conf/%s.template" % template_name)

# Fills template by values from given dictionary
def FillTemplate(template, values):
	for chunk in values.keys():
		template = template.replace(chunk, values[chunk])
	return template

# Retrieves data from jira and appends storage file with it
def GetAndSaveJiraFilteredData(filter_name):
	status = GetJiraFilterData(filter_name)
	return SaveUpdates(filter_name, status)

# Makes Wiki-syntax bar-chart markup for given data
def MakeWikiBarChart(data):
	dates = data.keys()
	dates.sort()
	result = "|| || %s ||" % " || ".join(date.strftime("%d/%m") for date in dates)
	for status in config["statuses_order"]:
	 	result += "\n| %s | " % status
	 	for date in dates:
	 		if data[date].has_key(status):
	 			result += " %s |" % data[date][status]
		 	else:
		 		result += " 0 |"
	return result

# Makes Wiki-syntax line (point) burndown markup for given data
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
		if (not weekends.match(date.strftime("%a")) or date == deadline or data.has_key(date)):
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

	commit = project_issue.sub("[%s-\\1@issues] " % config["project_abbr"], commit)

	if (commits.has_key(email)):
		commits[email].append(commit)
	else:
		commits[email] = [commit]

	print " - %s: %s" % (email, commit)

def BindLogs(key, source, title):
	co = ""
	if source.has_key(key):
		co = "\n-- ".join([item for item in source[key]])

	if len(co) > 0:
		co = "\n*%s:*\n-- %s" % (title, co)
	return co


def BindTeamLogs(team_name, teams, commits, worklog, personTemplate):
	result = "h3. %s Team\n{section}\n{column:width=49%%}\n" % team_name
	i = 1
	divide = True
	for email in teams[team_name]:
		half = (len(teams[team_name]) / 2)

		# Adding commits
		co = BindLogs(email, commits, "git commits")

		# Adding worklogs
		wl = BindLogs(teams[team_name][email], worklog, "jira worklogs")

		result += FillTemplate(personTemplate, {"##PERSON##": teams[team_name][email], "##PREVIOUS##": "", "##TODAY##": "", "##COMMITS##": co, "##WORKLOGS##": wl})
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


def GetWorkLogs(fromDate, tillDate):
	global soap, jiraAuth

	found = {}

	if (jiraAuth == None):
		InitJiraSOAP()

	# Getting Issues by Jql filter
	updatedIssues = {}
	issues = soap.getIssuesFromJqlSearch(jiraAuth, "project = %s AND updatedDate >= '%s 00:00' ORDER BY updated DESC" % (config["project_abbr"], fromDate.strftime("%Y/%m/%d")), 100)
	for i in issues:
		updatedIssues[i["key"]] = i["summary"]

	workLogs = {}
	for issueKey in updatedIssues.keys():
		print "%s: \"%s\":" % (issueKey, updatedIssues[issueKey])
		issues = soap.getWorklogs(jiraAuth, issueKey)
		for i in issues:
			# + 3 hours for England
			startDate = DateFromSet(i["startDate"]) + timedelta(hours = 3)
			if startDate.date() >= fromDate and startDate.date() < tillDate:
				value = "[%s@issues] (%s) %s - %s" % (issueKey, updatedIssues[issueKey], i["comment"].strip(" \n\r"), i["timeSpent"])
				AppendSubSet(workLogs, i["author"], value)
				print " + %s: %s (%s)" % (i["author"], i["comment"].strip(" \n\r"), i["timeSpent"])
				found[i["author"]] = True

	if (len(config["notified"]) > 0):
		jab = Jabber()

		for login in config["notified"].keys():
			if not found.has_key(login):
				jab.Message(config["notified"][login], "Please fill jira worklog for %s" % PrintableDate(fromDate))

		jab.Disconnect()

	return workLogs
