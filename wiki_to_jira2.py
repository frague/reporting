from rabbithole import *
from operator import itemgetter


tableExpr = re.compile("<table[^>]*>(%s+)</table>" % NotEqualExpression("</table>"), re.MULTILINE)
titleExpr = re.compile("title=\"([^\"]+)\"")
keyExpr = re.compile("\[([a-z]+\-\d+)@issues\]", re.IGNORECASE)
userExpr = re.compile("\[~([a-z]+)\]", re.IGNORECASE)

################################################################################################################


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

# Creates regexp for section searching
def MakeHtmlSectionRegexp(level, title=""):
	dPrefix = deRegexp("<h%s>" % level)
	return re.compile("<h%s><a[^>]*></a>%s</h%s>(%s+)" % (level, title, level, NotEqualExpression("<h%s" % level)), re.MULTILINE)

# Gets section by prefix from text (e.g. h6. Title ..... h6.)
# In case when there several sections with the same prefix in the text, title can be used
def GetHtmlSection(text, level, title=""):
	if not text:
		return ""

	found = MakeHtmlSectionRegexp(level, title).search(text)
	if found:
		return found.group(1)
	return found


# Parses table with header into a set of dectionaries, one per each row
def ParseHeadedTable(markup):
	cols = []
	result = []
	isHeader = False
	for row in markup.strip().split("<tr>"):
		if not row:
			continue
		values = re.split("</t[dh]>", re.sub("</t[dh]>$", "", re.sub("<(/tr|td|th)>", "", row).strip()))
		if not isHeader:
			cols = values
			isHeader = True
		else:
			item = {}
			for i in range(len(cols)):
				if cols[i] == "Priority":
					values[i] = long(values[i])
				item[cols[i]] = values[i]
			result.append(item)
	return result
				

################################################################################################################


ProfileNeeded()

containerPage = GetParameter("source")
version = GetParameter("version")
confidence = GetParameter("confidence")

if not containerPage or not version:
	print "[!] Usage: wiki_to_jira.py --profile=PROFILE_NAME --source=SOURCE_PAGE --version=VERSION [--confidence]"
	exit(0)

# jira versions
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



# Getting issues from wiki (sorted by priority)
soapW = SOAPpy.WSDL.Proxy(config["wiki_soap"])
wikiAuth = soapW.login(config["wiki"]["user"], config["wiki"]["password"])

page = soapW.getPage(wikiAuth, config["project_abbr"], containerPage)

rendered = soapW.renderContent(wikiAuth, config["project_abbr"], SOAPpy.Types.longType(long(page["id"])))
requirements = GetHtmlSection(rendered, 6, "Requirements")

wikiIssues = ParseHeadedTable(CleanHtmlTable(GetMatchGroup(requirements, tableExpr, 1)))
wikiIssues.sort(key=itemgetter("Priority"))
wikiIssues.reverse()


# Synching
seen = []
for index in range(len(wikiIssues)):
	issue = wikiIssues[index]
	summary = GetMatchGroup(issue["Title"], titleExpr, 1)
	page = soapW.getPage(wikiAuth, config["project_abbr"], summary)
	i = JiraIssue()
	i.summary = summary
#	i.key = GetMatchGroup(issue["JIRA"], keyExpr, 1)
	i.description = "%s\nh6. Detailed Description\n%s" % (issue["Description"], GetSection(page["content"], "h6.", "Detailed Description"))
#	i.assignee = GetMatchGroup(issue["Implementation Owner"], userExpr, 1)

	print "%s - %s" % (i.ToString(80), issue["Priority"])

