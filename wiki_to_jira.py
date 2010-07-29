from rabbithole import *

#############################################################

line = 80
regexpReserved = re.compile("([\[\]\{\}\.\?\*\+\-])")
separateRequirement = re.compile("^[#\-\*] ", re.MULTILINE)
excerptInclude = re.compile("\{excerpt-include:([^\|\}]+)[\|\}]")
wikiLink = re.compile("^\[(([^\|]+)\|){0,1}([^\]]+)\]$")
firstSentence = re.compile("^([^\n]+([\.\?\!][ \n$]|\n))")
jiraLink = re.compile("\[([a-z0-9]+-\d+)@issues\]", re.IGNORECASE)

ProfileNeeded()
containerPage = GetParameter("source")
version = GetParameter("version")

'''if not containerPage or not version:
	print "[!] Usage: wiki_to_jira.py --profile=PROFILE_NAME --source=SOURCE_PAGE --version=VERSION"
	exit(0)
	'''

def GetMatchGroup(haystack, expr, group):
	a = expr.search(haystack)
	if a:
		return a.group(group)
	return ""

def deRegexp(text):
	return regexpReserved.sub("\\\\\\1", text)

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

e = NotEqualExpression("{excerpt}")
excerptExpression = re.compile("\{excerpt\}(%s*)\{excerpt\}" % e)

# Gets section by prefix from text (e.g. h6. Title ..... h6.)
# In case when there several sections with the same prefix in the text, title can be used
def GetSection(text, prefix, title=""):
	if not text:
		return ""

#	print "\n----- Section \"%s %s\"" % (prefix, title)

	dPrefix = deRegexp(prefix)
	if title:
		title += "\n"

	section = re.compile("%s {0,1}%s(%s*)(\\n%s|$)" % (dPrefix, title, NotEqualExpression(prefix), dPrefix), re.MULTILINE)

	found = section.search(text)
	if found:
		return found.group(1)
	return found

# Return the only fist sentence from the text
def TakeFirstSentence(text):
	return GetMatchGroup(text, firstSentence, 1).strip() or text

def ProcessRequirementPage(page_title, issue):
	# TODO: Handle spaces in link
	requirement = GetWiki({"action": "getSource", "space": config["project_space"], "title": page_title})
	issue.summary = GetMatchGroup(requirement, excerptExpression, 1).strip()
	issue.description = GetSection(requirement, "h6.", "Description")
#	print "-----\n%s\n-----\n" % issue.description


# Processes issue by title (in case if issue excerpted)
def ProcessIssue(title, priority):
	issue = JiraIssue()
	issue.priority = priority

	key = GetMatchGroup(title, jiraLink, 1)
	if key:
		title = jiraLink.sub("", title).strip()
		issue.key = key

	excerpt = GetMatchGroup(title, excerptInclude, 1)
	if excerpt:
		ProcessRequirementPage(excerpt, issue)
	else:
		issue.summary = TakeFirstSentence(title)
		issue.description = title
	
	wikiIssues[issue.summary] = issue
	if key:
		wikiIssuesByKey[issue.key] = issue

	return issue


# List separate issues in the given text (section)
def ListIssues(text, priority):
	if not text:
		return

	for i in separateRequirement.split(text):
		if i:
			issue = ProcessIssue(i.strip(), config["priorities"][priority])
			action = " "
			if issue.key:
				if jiraIssuesByKey.has_key(issue.key):
					# Issue already exists on jira - compare
					pass
				else:
					# jira issue has been deleted - notify user to update wiki
					pass
			else:
				if jiraIssues.has_key(issue.summary):
					# Shouldn't occur ...
					pass
				else:
					# jira issue doesn't exist - create new
					issue.project = config["project_abbr"]
					issue.reporter = "nbogdanov"

					issue.Connect(soap, jiraAuth)
					issue.Create()
					issue.SetVersion(versionId)
					action = "+";

			print " [%s] %s" % (action, issue.ToString(line))

########################################################################################################################

soap = SOAPpy.WSDL.Proxy(config["jira_soap"])
jiraAuth = soap.login(config["jira"]["user"], config["jira"]["password"])

versionId = None
for v in soap.getVersions(jiraAuth, config["project_abbr"]):
	if v["name"] == version:
		versionId = v["id"]
		break

if not versionId:
	print "[!] jira version not found!"
	exit(0)




## Jira issues for version

print "Issues in jira:"

jiraIssues = {}			# TODO: Not needed, remove
jiraIssuesByKey = {}

issue = JiraIssue()
issue.Connect(soap, jiraAuth)
issues = soap.getIssuesFromJqlSearch(jiraAuth, "project = %s AND fixVersion = %s" % (config["project_abbr"], version), 100)

for i in issues:
	issue.Parse(i)
	jiraIssues[issue.summary] = issue
	jiraIssuesByKey[issue.key] = issue
	print " %s" % (issue.ToString(line))


## Issues on wiki

wikiIssues = {}
wikiIssuesByKey = {}

page = GetWiki({"action": "getSource", "space": config["project_space"], "title": containerPage})

requirements = GetSection(page, "h4.", "Requirements")
[ListIssues(GetSection(requirements, "h6.", priority), priority) for priority in config["priorities"].keys()]



exit(0)

























# Create new issues
for i in cqIssues.keys():
	v = cqIssues[i]

	if v["State"] != "Closed":
		descr = re.sub("([^>])(\n<)", "\\1{code}\\2", v["Steps_Description"])
		descr = re.sub("(>\n)([ \t\n]*[^< \t\n])", "\\1{code}\\2", descr)

		print "[+] %s: %s" % (v["id"], v["Title"][0:line])
#		print descr

		newIssue = soap.createIssue(jiraAuth, {"project": config["project_abbr"], "type": "1", "priority": v["Priority"][0:1], "summary": "%s: %s" % (v["id"], v["Title"]), "description": descr, "assignee": config["QAAssignee"], "reporter": "nbogdanov"})
		soap.updateIssue(jiraAuth, newIssue.key, [{"id": "fixVersions", "values": [config["QAVersionId"]]}])



'''
for i in issues:
	issue.Parse(i)
	n = issue.Number()

	print "%s: %s" % (issue.key, issue.status)

	if (issue.status != "6"):
		if n >= 645 and n <=716:
			issue.Update([{"id": "fixVersion", "values": ["10721", "10725"]}])

		if n > 716 and n <=762:
			issue.Update([{"id": "fixVersion", "values": ["10721", "10726"]}])'''

'''if re.search(" same ", issue.summary):
		print "-- %s" % issue.summary
		issue.Update([{"id": "priority", "values": "3"}, {"id": "assignee", "values": "tgautier"}])'''

#		issue.Update([{"id": "priority", "values": "3"}])


'''

[
059.        {"id": "summary", "values": ['[Updated] Issue created with Python'] },
060. 
061.        # Change issue type to 'New feature'
062.        {"id":"issuetype", "values":'2'},
063. 
064.        # Setting a custom field. The id (10010) is discoverable from
065.        # the database or URLs in the admin section
066. 
067.        {"id": "customfield_10010", "values": ["Random text set in updateIssue method"] },
068. 
069.        {"id":"fixVersions", "values":['10331']},
070.        # Demonstrate setting a cascading selectlist:
071.        {"id": "customfield_10061", "values": ["10098"]},
072.        {"id": "customfield_10061_1", "values": ["10105"]},
073.        {"id": "duedate", "values": datetime.date.today().strftime("%d-%b-%y")}
074. 
075.        ]

'''