from rabbithole import *
from operator import itemgetter
import xmlrpclib


tableExpr = re.compile("<table[^>]*>(%s+)</table>" % NotEqualExpression("</table>"), re.MULTILINE)
titleExpr = re.compile("title=\"([^\"]+)\"")
urlExpr = re.compile("href=\"([^\"]+)\"")
keyExpr = re.compile("\[([a-z]+\-\d+)@issues\]", re.IGNORECASE)
keyPageExpr = re.compile("\|\| *JIRA *\|([^\|]*)\|", re.IGNORECASE)
userExpr = re.compile("\[~([a-z]+)\]", re.IGNORECASE)
assigneeExpr = re.compile("\|\| *Implementation Owner *\| *([a-z\[\]\~]+ *)\|", re.IGNORECASE)
confidenceExpr = re.compile("\|\| *Confidence *\|([^\|]+)\|", re.IGNORECASE)
statusExpr = re.compile("\|\| *Status *\|([^\|]+)\|", re.IGNORECASE)
descriptionExpr = re.compile("\|\| *Description *\|([^\|]+)\|", re.IGNORECASE)

wikiRef = "h6. Requirement on the wiki:"

################################################################################################################


crlf = re.compile("\n{3,}")
def LineEndings(text):
	text = text.replace("\r", "")
	return crlf.sub("\n\n", text)

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
	url = GetMatchGroup(issue["Title"], urlExpr, 1)

	pageName = deHtml(summary)
	page = wikiServer.confluence1.getPage(wikiToken, config["project_abbr"], pageName)
	
	i = JiraIssue()
	i.Connect(soap, jiraAuth)

	key = GetMatchGroup(page["content"], keyPageExpr, 1)
	i.key = GetMatchGroup(key, keyExpr, 1)

	i.issuetype = "6"
	i.project = config["project_abbr"]
	i.summary = summary

	descr = GetSection(page["content"], "h6.", "Detailed Description")
	if descr:
		descr = descr.replace("{excerpt}", "")

	d = GetMatchGroup(page["content"], descriptionExpr, 1)
	i.description = LineEndings("%s\nh6. Detailed Description:\n%s\n \n%s\n%s%s" % (d.replace("{excerpt}", ""), descr, wikiRef, config["wiki"]["server"], url))

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

			confidence = GetMatchGroup(page["content"], confidenceExpr, 1)
			if confidence and confidence.strip() != "(/)100%" and (ji.status == "5" or ji.status == "6"):
				page["content"] = confidenceExpr.sub("|| Confidence | (/)100% |", page["content"])
				page["content"] = statusExpr.sub("|| Status | Closed |", page["content"])
				wikiServer.confluence1.storePage(wikiToken, page)
				action = "x"

			if ji.status == "10068" or ji.status == "10078":
				# If issue is in "To Be Reviewed" or in "To Be Accepted" status - ignore re-assignments
				ji.assignee = i.assignee
			
			if ji.Equals(i):
				# Issues are the same
				pass
			else:
				# Issues aren't equal - update to newer
				action = "@"
				try:
					ji.UpdateFrom(i)
					ji.SetVersion([versionId, backlogVersionId])
				except:
					action = "!"
					
		else:
			# Reference to jira issue exists on the wiki but issue wasn't returned by request
			# Need to request a single issue separately and set proper versions
			i.Fetch()
			action = "v"
			try:
				i.SetVersion([versionId, backlogVersionId])
			except:
				action = "!"
	else:
		action = "+"
		# New issue - create
		i.Create()
		i.SetVersion([versionId, backlogVersionId])
		# Update wiki page with jira key
		page["content"] = keyPageExpr.sub("|| JIRA | [%s@issues] |" % i.key, page["content"])
		wikiServer.confluence1.storePage(wikiToken, page)

	print "[%s] %s - %s (%s)" % (action, i.ToString(80), issue["Priority"], i.assignee)

print "\n-- Moving requirements removed from sprint to the Backlog:"

# Remove not met issues from sprint
for key in jiraIssuesByKey.keys():
	if not key in seen:
		action = " "
		ji = jiraIssuesByKey[key]
		if wikiRef in ji.description:
			ji.SetVersion([backlogVersionId])
			action = "-"
		print "[%s] %s" % (action, ji.ToString(80))


