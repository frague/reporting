from rabbithole import *

ProfileNeeded()

commits = {}
personTemplate = GetTemplate("person")

# Getting command line parameters
notify = GetParameter("notify")
ignore = GetParameter("ignore").split(",")


######################################################################################
# Git commits

print "-- Fetching git commits: -----------------------------------------------"

# Fetch teammembers repositories
rep_path = config["repository_path"]
for team in config["teams"].keys():
	[GetStdoutOf("fetchrep.bat", "%s %s" % (rep, rep_path)) for rep in config["teams"][team]]

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
	chunks = {"##TODAY##": today.strftime("%Y-%m-%d"), "##ABBR##": config["project_abbr"]}
	for team in config["teams"].keys():
		chunks["##%s##" % team] = BindTeamLogs(team, config["teams"], commits, workLogs, personTemplate)
	page = FillTemplate(GetTemplate(config["report_template"]), chunks)

	WriteFile("temp1.tmp", page)
	#GetWiki({"action": "storePage", "space": config["personal_space"], "title": "gitlog + %s report template" % today, "file": "temp1.tmp", "parent": config["parent_page"]})
	GetWiki({"action": "storeNews", "space": config["project_space"], "title": "%s Daily Report" % today.strftime("%Y.%m.%d"), "file": "temp1.tmp"})
	os.remove("temp1.tmp")

print "Done"
