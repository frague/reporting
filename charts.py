from rabbithole import *

#####################################################################
# Phase & Project total progress

print "-- Updating progress charts: -------------------------------------------"
print "Reading templates"

page = GetTemplate("ch_progress")
sprint = GetTemplate("single_burndown")

# Phase Graphs
print "Sprint: reading data form jira, updating stored data"
phase_data = GetAndSaveJiraFilteredData("%s" % config["phase"])

#  Barchart
print "Sprint: building barcharts and burn-down diagrams"
phase_bars = MakeWikiBarChart(phase_data)
page = FillTemplate(page, {"##PHASECHART##": phase_bars, "##PHASETITLE##": "Sprint Progress Chart"})

#  Burndown
phase_burndown = MakeWikiBurndownChart(phase_data, config["sprintEnd"])
page = FillTemplate(page, {"##PHASEBURNCHART##": phase_burndown, "##PHASEBURNTITLE##": "Sprint Burndown diagram"})
sprint = FillTemplate(sprint, {"##PHASEBURNCHART##": phase_burndown, "##PHASEBURNTITLE##": "Sprint #%s Burndown diagram" % config["currentSprint"]})

# Total progress
#  Burndown
'''print "Phase: reading data form jira, updating stored data"
total_data = GetAndSaveJiraFilteredData("ProductBacklog")

print "Phase: building barcharts and burn-down diagrams"
total_burndown = MakeWikiBurndownChart(total_data, config["phaseEnd"])
page = FillTemplate(page, {"##TOTALBURNCHART##": total_burndown, "##TOTALBURNTITLE##": "Phase %s Burndown diagram" % config["phase"]})

# Total progress (Full)
#  Burndown
print "Phase (full): reading data form jira, updating stored data"
total_full_data = GetAndSaveJiraFilteredData("ProductBacklogWithSubtasks")

print "Phase (full): building barcharts and burn-down diagrams"
total_full_burndown = MakeWikiBurndownChart(total_full_data, config["phaseEnd"])
page = FillTemplate(page, {"##TOTALBURNCHARTFULL##": total_full_burndown, "##TOTALBURNFULLTITLE##": "Phase %s Burndown diagram (with subtasks)" % config["phase"]})'''


print "Publishing to wiki"
WriteFile("temp.tmp", page)
GetWiki({"action": "storePage", "space": config["personal_space"], "title": "%s Progress Charts" % today, "file": "temp.tmp", "parent": config["parent_page"]})
os.remove("temp.tmp")

WriteFile("temp.tmp", sprint)
GetWiki({"action": "storePage", "space": config["personal_space"], "title": "%s Sprint Progress" % config["currentSprint"], "file": "temp.tmp", "parent": config["parent_page"]})
os.remove("temp.tmp")

print "Done"
