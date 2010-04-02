from rabbithole import *

commits = {}
personTemplate = GetTemplate("person")
teams = yaml.load(ReadFile("conf/teams.yaml"))

# Getting command line parameters
notify = "--notify" in sys.argv
ignore = []
for key in sys.argv:
	if ignore_key.match(key):
		ignore = ignore_key.sub("", key).split(",")


######################################################################################
# Git commits

print "-- Fetching git commits: -----------------------------------------------"

# Fetch teammembers repositories
for team in teams.keys():
	[GetStdoutOf("fetchrep.bat", "%s" % rep) for rep in teams[team]]

# Getting log
text = GetStdoutOf("gitlog.bat", "%s %s" % (lastWorkday.strftime("%Y-%m-%d"), today.strftime("%Y-%m-%d")))
# Split into lines and treat each
[AddCommit(line, commits) for line in text.split("\n")]

######################################################################################
# Jira worklogs

print "\n-- Fetching jira worklogs: ---------------------------------------------"
workLogs = GetWorkLogs(lastWorkday, today) 

if notify:
	# Notify guys who forgot to fill worklog via give engine
	print "\n-- Sending IM notifications: -------------------------------------------"
	RequestWorklogs(lastWorkday, workLogs, config["notified_skype"], Skype(), commits, ignore)
else:
	# Populate template with received values
	page = FillTemplate(GetTemplate("report"), {"##SARATOV##": BindTeamLogs("Saratov", teams, commits, workLogs, personTemplate), "##US##": BindTeamLogs("US", teams, commits, workLogs, personTemplate), "##TODAY##": today.strftime("%Y-%m-%d")})

	WriteFile("temp1.tmp", page)
	#GetWiki({"action": "storePage", "space": "~nbogdanov", "title": "gitlog + %s report template" % today, "file": "temp1.tmp", "parent": "BigRock Reporting automation"})
	GetWiki({"action": "storeNews", "space": "ToRS", "title": "%s Daily Report" % today.strftime("%Y.%m.%d"), "file": "temp1.tmp"})
	os.remove("temp1.tmp")

print "Done"
