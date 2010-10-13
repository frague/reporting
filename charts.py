from rabbithole import *

ProfileNeeded()

#####################################################################
# Phase & Project total progress

print "-- Updating progress charts: -------------------------------------------"
print "Reading templates"

page = GetTemplate(config["charts_template"])
sprint = GetTemplate("single_burndown")

data = {}
charts_data = {}
for set in [config["charts_burndown"], config["charts_bars"], config["charts_timing"]]:
	for key in set.keys():
		dataSet = set[key]

		if key.find("TIMING") >= 0:
			charts_data[key] = GetAndSaveJiraVersionTimings(config["project_abbr"], dataSet[0])
		else:
			if len(dataSet) > 0:
				if not data.has_key(dataSet[0]):
					data[dataSet[0]] = GetAndSaveJiraVersionIssues(config["project_abbr"], dataSet[0])
				charts_data[key] = data[dataSet[0]]

		print "jira version \"%s\" data loaded for %s." % (dataSet[0], key)


print "-- Bar charts: ---------------------------------------------------------"
for key in config["charts_bars"].keys():
	page = FillTemplate(page, {"##%s##" % key: MakeWikiBarChart(charts_data[key], key)})

print "-- Burn-down diagrams: -------------------------------------------------"
burns = config["charts_burndown"]
for key in burns.keys():
	value = burns[key]
	page = FillTemplate(page, {"##%s##" % key: MakeWikiBurndownChart(charts_data[key], config[value[1]], key)})

print "-- Burn-down timing diagrams: ------------------------------------------"
timings = config["charts_timing"]
for key in timings.keys():
	value = timings[key]
	page = FillTemplate(page, {"##%s##" % key: MakeWikiTimingChart(charts_data[key], config[value[1]], key)})


print "Publishing to wiki"
WriteFile("temp.tmp", page)
GetWiki({"action": "storePage", "space": config["personal_space"], "title": "%s %s Progress Charts" % (config["project_abbr"], today), "file": "temp.tmp", "parent": config["parent_page"]})
os.remove("temp.tmp")

print "Done"
