from rabbithole import *
from operator import itemgetter
import xmlrpclib


tableExpr = re.compile("<table[^>]*>(%s+)</table>" % NotEqualExpression("</table>"), re.MULTILINE)
titleExpr = re.compile("title=\"([^\"]+)\"")
keyExpr = re.compile("\[([a-z]+\-\d+)@issues\]", re.IGNORECASE)
keyPageExpr = re.compile("\|\| *JIRA *\|([^\|]*)\|", re.IGNORECASE)
userExpr = re.compile("\[~([a-z]+)\]", re.IGNORECASE)
assigneeExpr = re.compile("\|\|Implementation Owner\|([a-z\[\]\~]+)\|", re.IGNORECASE)

################################################################################################################


crlf = re.compile("[\n\r]+")
def LineEndings(text):
	return crlf.sub("\n", text)

# Creates regexp for section searching
def MakeSectionRegexp(prefix, title=""):
	dPrefix = deRegexp(prefix)
#	if title:
#		title += "\\n"
#	print "(%s {0,1}%s)(%s*)(\\n%s|$)" % (dPrefix, title, NotEqualExpression(prefix), dPrefix)
	return re.compile("(%s {0,1}%s)(%s*)(\\n%s|$)" % (dPrefix, title, NotEqualExpression(prefix), dPrefix), re.MULTILINE)

# Gets section by prefix from text (e.g. h6. Title ..... h6.)
# In case when there several sections with the same prefix in the text, title can be used
def GetSection(text, prefix, title=""):
	if not text:
		return ""

#	print "\n----- Section \"%s %s\"" % (prefix, title)
	found = MakeSectionRegexp(prefix, title).search(text)
	if found:
		return found.group(2).strip()
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
	return ""


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
print "-- Existing jira issues by version \"%s\" (%s)" % (version, len(issues))
for i in issues:
	issue = JiraIssue()
	issue.Connect(soap, jiraAuth)
	issue.Parse(i)
	issue.description = LineEndings(issue.description)
	jiraIssues[issue.summary] = issue	# Do we need this?
	jiraIssuesByKey[issue.key] = issue
#	print " %s" % (issue.ToString(line))



# Getting issues from wiki (sorted by priority)
wikiServer = xmlrpclib.ServerProxy(config["wiki_xmlrpc"])
wikiToken = wikiServer.confluence1.login(config["wiki"]["user"], config["wiki"]["password"])


page = wikiServer.confluence1.getPage(wikiToken, config["project_abbr"], containerPage)

rendered = wikiServer.confluence1.renderContent(wikiToken, config["project_abbr"], page.get("id"), "")
requirements = GetHtmlSection(rendered, 6, "Requirements")
wikiIssues = ParseHeadedTable(CleanHtmlTable(GetMatchGroup(requirements, tableExpr, 1)))
wikiIssues.sort(key=itemgetter("Priority"))
#wikiIssues.reverse()		# Makes issues sorted by priority from GREATER to LESSER

print "-- Requirements listed on the wiki page \"%s\" (%s)" % (containerPage, len(wikiIssues))

# Synching
flag = True

seen = []
for index in range(len(wikiIssues)):
	issue = wikiIssues[index]
	summary = GetMatchGroup(issue["Title"], titleExpr, 1)

	pageName = deHtml(summary)
	page = wikiServer.confluence1.getPage(wikiToken, config["project_abbr"], pageName)
	
	i = JiraIssue()
	i.Connect(soap, jiraAuth)

	key = GetMatchGroup(page["content"], keyPageExpr, 1)
	i.key = GetMatchGroup(key, keyExpr, 1)

	i.project = config["project_abbr"]
	i.summary = summary
	i.description = LineEndings("%s\nh6. Detailed Description\n%s" % (issue["Description"], GetSection(page["content"], "h6.", "Detailed Description")))
	# DeHTML
	i.summary = i.summary.replace("&quot;", "\"")

	i.assignee = GetMatchGroup(page["content"], assigneeExpr, 1)
	if userExpr.match(i.assignee):
		i.assignee = GetMatchGroup(i.assignee, userExpr, 1)
	else:
		i.assignee = ""

	action = " "
	if i.key:
		seen.append(i.key)
		if jiraIssuesByKey.has_key(i.key):
			ji = jiraIssuesByKey[i.key] 
			if ji.Equals(i):
				# Issues are the same
				pass
			else:
				# Issues aren't equal - update to newer
				ji.UpdateFrom(i)
				ji.SetVersion([versionId, backlogVersionId])
				action = "@"
		else:
			# Reference to jira issue exists on the wiki but issue wasn't returned by request
			# Need to request a single issue separately and set proper versions
			i.Fetch()
			i.SetVersion([versionId, backlogVersionId])
			action = "v"
	else:
		action = "+"
		# New issue - create
		i.Create()
		i.SetVersion([versionId, backlogVersionId])
		# Update wiki page with jira key
		page["content"] = keyPageExpr.sub("|| JIRA | [%s@issues] |" % i.key, page["content"])
		wikiServer.confluence1.storePage(wikiToken, page)

	print "[%s] %s - %s (%s)" % (action, i.ToString(80), issue["Priority"], i.assignee)

# Remove not met issues from sprint
for key in jiraIssuesByKey.keys():
	if not key in seen:
		ji = jiraIssuesByKey[key]
		ji.SetVersion([backlogVersionId])
		print "[-] %s" % ji.ToString(80)

