from rabbithole import *

ProfileNeeded()

commits = {}
personTemplate = GetTemplate("person")

# Getting command line parameters
notify = GetParameter("notify")
ignore = GetParameter("ignore").split(",")

add = GetParameter("add")
add_project = None
if add:
	add_project = GetProfile(add)["project_abbr"]




######################################################################################
# Git commits

print "-- Fetching git commits: -----------------------------------------------"

# Fetch teammembers repositories
rep_path = config["repository_path"] + ".git"
for team in config["teams"].keys():
	[GetStdoutOf("git", "--git-dir=\"%s\" fetch %s" % (rep_path, rep)) for rep in config["teams"][team]]

# Getting log
lastWorkingDay = lastWorkday.strftime("%Y-%m-%d")
text = GetStdoutOf("git", "--git-dir=\"%s\" log --after=\"%s 00:00:00\" --all --format=format:\"%%ci|%%ce|%%s|%%ai\"" % (rep_path, lastWorkingDay))


#Split into lines and treat each
[AddCommit(line, commits, lastWorkingDay) for line in text.split("\n")]

######################################################################################
# Jira worklogs

print "\n-- Fetching jira worklogs: ---------------------------------------------"
workLogs = GetWorkLogs(lastWorkday, today, None, add_project) 

if notify:
	# Notify guys who forgot to fill worklog via give engine
	print "\n-- Sending IM notifications: -------------------------------------------"
	RequestWorklogs(lastWorkday, workLogs, config["notified_skype"], Skype(), commits, ignore)
else:
	# Populate template with received values
	chunks = {"##TODAY##": today.strftime("%Y-%m-%d"), "##TOMORROW##": tomorrow.strftime("%Y-%m-%d"), "##ABBR##": config["project_abbr"]}
	for team in config["teams"].keys():
		chunks["##%s##" % team] = BindTeamLogs(team, config["teams"], commits, workLogs, personTemplate)
	page = FillTemplate(GetTemplate(config["report_template"]), chunks)

	print "\n-- Publishing on wiki: -------------------------------------------------"

	wikiServer = xmlrpclib.ServerProxy(config["wiki_xmlrpc"])
	wikiToken = wikiServer.confluence1.login(config["wiki"]["user"], config["wiki"]["password"])

	SaveWikiNews(wikiServer, wikiToken, config["project_space"], "%s Daily Status Update" % today.strftime("%Y-%m-%d"), page)

print "Done."

