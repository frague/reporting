from rabbithole import *

ProfileNeeded()

#####################################################################
# Phase & Project total progress

print "-- Updating progress charts: -------------------------------------------"
print "Reading templates"

if weekends.match(today.strftime("%a")):
	print "[!] Weekend - exiting!"
	exit(0)


wikiServer = xmlrpclib.ServerProxy(config["wiki_xmlrpc"])
wikiToken = wikiServer.confluence1.login(config["wiki"]["user"], config["wiki"]["password"])

page = GetTemplate(config["charts_template"])
sprint = GetTemplate("single_burndown")

# Calculates tasks statuses and updates caches
def GetAndUpdateStatistics():
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

			print " * jira version \"%s\" data loaded for %s." % (dataSet[0], key)
	return charts_data

# Fills given template with given sets of charts
def BuildChartsFor(page, bars, burns, timings):
	print "\n---- Start filling the template:"
	if bars and len(bars) > 0:
		print "-- Bar charts: ---------------------------------------------------------"
		for key in bars.keys():
			page = FillTemplate(page, {"##%s##" % key: MakeWikiBarChart(charts_data[key], key)})

	if burns and len(burns) > 0:
		print "-- Burn-down diagrams: -------------------------------------------------"
		for key in burns.keys():
			value = burns[key]
			page = FillTemplate(page, {"##%s##" % key: MakeWikiBurndownChart(charts_data[key], config[value[1]], key)})

	if timings and len(timings) > 0:
		print "-- Burn-down timing diagrams: ------------------------------------------"
		for key in timings.keys():
			value = timings[key]
			page = FillTemplate(page, {"##%s##" % key: MakeWikiTimingChart(charts_data[key], config[value[1]], key)})
	return page

# Updates wiki page or creates the new one
def UpdateWikiPage(space, page_name, content, parent_page = "", comment = ""):
	global wikiServer, wikiToken

	try:
		# Getting existing page for update
		page = wikiServer.confluence1.getPage(wikiToken, space, page_name)
		page["content"] = content
		wikiServer.confluence1.updatePage(wikiToken, page, {"minorEdit": True, "versionComment": comment})
	except:
		# New page
		page = {"title": page_name, "space": space, "content": content}
		if parent_page:
			try:
				parent = wikiServer.confluence1.getPage(wikiToken, space, parent_page)
			except:
				print "[!] Error getting parent page \"%s\" in space \"%s\"" % (parent_page, space)
				return False

			page["parentId"] = parent["id"]
		wikiServer.confluence1.storePage(wikiToken, page)
	print "- Page \"%s\" has been successfully updated on wiki" % page_name
	return True


charts_data = GetAndUpdateStatistics()

page = BuildChartsFor(GetTemplate(config["charts_template"]), config["charts_bars"], config["charts_burndown"], config["charts_timing"])
UpdateWikiPage(config["personal_space"], "%s %s Progress Charts" % (config["project_abbr"], today), page, config["parent_page"], "Daily update")

page = BuildChartsFor(GetTemplate("charts_report"), {}, config["charts_burndown"], config["charts_timing"])
UpdateWikiPage(config["project_space"], "Trends", page, "Reporting", "Daily update")

print "Done"
