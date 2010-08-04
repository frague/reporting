from rabbithole import *

#############################################################

line = 80
regexpReserved = re.compile("([\[\]\{\}\.\?\*\+\-])")
separateRequirement = re.compile("^[#\-\*] ", re.MULTILINE)
excerptInclude = re.compile("\{excerpt-include:([^\|\}]+)[\|\}]")
wikiLink = re.compile("^\[(([^\|]+)\|){0,1}([^\]]+)\]$")
jiraLink = re.compile("\[([a-z0-9]+-\d+)@issues\]", re.IGNORECASE)
doubleList = re.compile("^[#*]([#*]+ )", re.MULTILINE)


firstSentence = re.compile("^([^\n]+([\.\?\!][ \n$]|\n))")


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


# Creates regexp for section searching
def MakeSectionRegexp(prefix, title=""):
	dPrefix = deRegexp(prefix)
	if title:
		title += "\n"
	return re.compile("(%s {0,1}%s)(%s*)(\\n%s|$)" % (dPrefix, title, NotEqualExpression(prefix), dPrefix), re.MULTILINE)

# Gets section by prefix from text (e.g. h6. Title ..... h6.)
# In case when there several sections with the same prefix in the text, title can be used
def GetSection(text, prefix, title=""):
	if not text:
		return ""

#	print "\n----- Section \"%s %s\"" % (prefix, title)
	found = MakeSectionRegexp(prefix, title).search(text)
	if found:
		return found.group(2)
	return found

# Substitutes content of section in text.
# If section has not been found, new content will be appended to the text
def SubstituteSection(text, new_content, prefix, title=""):
	new_text = MakeSectionRegexp(prefix, title).sub("\\1%s\\4" % new_content, text)
	if new_text == text:
		# Appending new content to the end
		new_text = "%s\n%s %s\n%s\n" % (text, prefix, title, new_content)
	return new_text

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
def ListIssues(prefix, title):
	global requirements, page, updateWiki, metKeys

	text = GetSection(requirements, prefix, title)
	if not text:
#		print "[!] Section %s \"%s\" is not found" % (prefix, title)
		return

	sectionUpdated = False
	new_content = ""

	for i in separateRequirement.split(text):
		if i:
			issue = ProcessIssue(doubleList.sub("\\1", i).strip(), config["priorities"][priority])
			action = " "
			if issue.key:
				metKeys.append(issue.key)

				if jiraIssuesByKey.has_key(issue.key):
					# Issue already exists on jira - compare
					if not issue.Equals(jiraIssuesByKey[issue.key]):
						action = "@"
						jiraIssuesByKey[issue.key].UpdateFrom(issue)
				else:
					# jira issue has been deleted - notify user to update wiki
					action = "?"
			else:
				sectionUpdated = True
				if jiraIssues.has_key(issue.summary):
					# Shouldn't occur ...
					i = "[%s@issues] %s" % (jiraIssues[issue.summary].key, i)
				else:
					# jira issue doesn't exist - create new
					issue.project = config["project_abbr"]
					issue.reporter = "nbogdanov"

					issue.Connect(soap, jiraAuth)
					issue.Create()
					issue.SetVersion([versionId, backlogVersionId])
					action = "+";
					i = "[%s@issues] %s" % (issue.key, i)
					metKeys.append(issue.key)

			new_content += "# %s\n" % i.strip()

			print " [%s] %s" % (action, issue.ToString(line))

#	print "\n-----------------------------------------\n" + new_content + "\n-----------------------------------------\n"

	if sectionUpdated:	
		updateWiki = True
		page = SubstituteSection(requirements, new_content, prefix, title)
		

########################################################################################################################

updateWiki = False

soap = SOAPpy.WSDL.Proxy(config["jira_soap"])
jiraAuth = soap.login(config["jira"]["user"], config["jira"]["password"])

versionId = None
backlogVersionId = None
for v in soap.getVersions(jiraAuth, config["project_abbr"]):
	if v["name"] == version:
		versionId = v["id"]
	if v["name"] == "Product Backlog":
		backlogVersionId = v["id"]

if not versionId or not backlogVersionId:
	print "[!] jira version is not found!"
	exit(0)


## Jira issues for version

#print "Issues in jira:"

jiraIssues = {}			# TODO: Not needed, remove
jiraIssuesByKey = {}
metKeys = []

issues = soap.getIssuesFromJqlSearch(jiraAuth, "project = '%s' AND fixVersion = '%s'" % (config["project_abbr"], version), 100)

for i in issues:
	issue = JiraIssue()
	issue.Connect(soap, jiraAuth)
	issue.Parse(i)
	jiraIssues[issue.summary] = issue
	jiraIssuesByKey[issue.key] = issue
#	print " %s" % (issue.ToString(line))


## Issues on wiki

print "Issues on wiki:"

wikiIssues = {}
wikiIssuesByKey = {}

page = re.sub("^Page source\n", "", GetWiki({"action": "getSource", "space": config["project_space"], "title": containerPage}))

requirements = GetSection(page, "h4.", "Requirements")

# Sync existing issues
[ListIssues("h6.", priority) for priority in config["priorities"].keys()]

'''# Remove deleted issues from jira
for key in jiraIssuesByKey.keys():
	if not key in metKeys:
		print " [-] %s" % jiraIssuesByKey[key].ToString(line)
		jiraIssuesByKey[key].Delete()'''

# Put unsynched jira issues to separate section
updateWiki = True
jiraOnly = ""
for key in jiraIssuesByKey.keys():
	if not key in metKeys:
		print " [#] %s" % jiraIssuesByKey[key].ToString(line)
		jiraOnly += "# [%s@issues] %s\n" % (key, jiraIssuesByKey[key].summary)

requirements = SubstituteSection(requirements, jiraOnly, "h6.", "Issues in jira only")
page = SubstituteSection(page, requirements, "h4.", "Requirements")

# Update wiki with jira keys
if updateWiki:
	WriteFile("temp.tmp", page)
	GetWiki({"action": "storePage", "space": config["project_space"], "title": containerPage, "file": "temp.tmp"})
	os.remove("temp.tmp")
	print "[!] wiki page has been updated"
