from rabbithole import *

currentSprint = "10";
sprintEnd = datetime.date(2010, 3, 19)
phaseEnd = datetime.date(2010, 3, 26)



#####################################################################
# Phase & Project total progress

page = GetTemplate("progress")
sprint = GetTemplate("single_burndown")

# Phase Graphs
phase_data = GetAndSaveJiraFilteredData("phase2.5sprint%s" % currentSprint)

#  Barchart
phase_bars = MakeWikiBarChart(phase_data)
page = FillTemplate(page, {"##PHASECHART##": phase_bars, "##PHASETITLE##": "Sprint Progress Chart"})

#  Burndown
phase_burndown = MakeWikiBurndownChart(phase_data, sprintEnd)
page = FillTemplate(page, {"##PHASEBURNCHART##": phase_burndown, "##PHASEBURNTITLE##": "Sprint Burndown diagram"})
sprint = FillTemplate(sprint, {"##PHASEBURNCHART##": phase_burndown, "##PHASEBURNTITLE##": "Sprint #%s Burndown diagram" % currentSprint})

# Total progress
#  Burndown
total_data = GetAndSaveJiraFilteredData("ProductBacklog")

total_burndown = MakeWikiBurndownChart(total_data, phaseEnd)
page = FillTemplate(page, {"##TOTALBURNCHART##": total_burndown, "##TOTALBURNTITLE##": "Phase 2.5 Burndown diagram"})

# Total progress (Full)
#  Burndown
total_full_data = GetAndSaveJiraFilteredData("ProductBacklogWithSubtasks")

total_full_burndown = MakeWikiBurndownChart(total_full_data, phaseEnd)
page = FillTemplate(page, {"##TOTALBURNCHARTFULL##": total_full_burndown, "##TOTALBURNFULLTITLE##": "Phase 2.5 Burndown diagram (with subtasks)"})


WriteFile("temp.tmp", page)
GetWiki({"action": "storePage", "space": "~nbogdanov", "title": "%s Progress Charts" % today, "file": "temp.tmp", "parent": "BigRock Reporting automation"})
os.remove("temp.tmp")

WriteFile("temp.tmp", sprint)
GetWiki({"action": "storePage", "space": "~nbogdanov", "title": "%s Sprint Progress" % currentSprint, "file": "temp.tmp", "parent": "BigRock Reporting automation"})
os.remove("temp.tmp")

print "Done"
