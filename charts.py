from rabbithole import *

ProfileNeeded()

#####################################################################
# Phase & Project total progress

print "-- Updating progress charts: -------------------------------------------"
print "Reading templates"

page = GetTemplate(config["charts_template"])
sprint = GetTemplate("single_burndown")

data = {}
for set in [config["charts_burndown"], config["charts_bars"]]:
	for dataSet in set.values():
		if len(dataSet) > 0 and not data.has_key(dataSet[0]):

			data[dataSet[0]] = GetAndSaveJiraVersionIssues(config["project_abbr"], dataSet[0])
			
			print "Filter %s data loaded." % dataSet[0]
#			print data[dataSet[0]]

print "-- Bar charts: ---------------------------------------------------------"
for key in config["charts_bars"].keys():
	page = FillTemplate(page, {"##%s##" % key: MakeWikiBarChart(data[config["charts_bars"][key][0]], key)})

print "-- Burn-down diagrams: -------------------------------------------------"
burns = config["charts_burndown"]
for key in burns.keys():
	value = burns[key]
	page = FillTemplate(page, {"##%s##" % key: MakeWikiBurndownChart(data[value[0]], config[value[1]], key)})


print "Publishing to wiki"
WriteFile("temp.tmp", page)
GetWiki({"action": "storePage", "space": config["personal_space"], "title": "%s %s Progress Charts" % (config["project_abbr"], today), "file": "temp.tmp", "parent": config["parent_page"]})
os.remove("temp.tmp")

print "Done"
