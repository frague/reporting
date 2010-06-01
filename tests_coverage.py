#!/usr/bin/python

from rabbithole import *

stats = {}
percents = re.compile("<strong>([^<]+)</strong>[\n ]*&nbsp;[\n ]*(\d+)%", re.MULTILINE)

def collectStat(matchObj):
	global stats

	measure = matchObj.group(1)
	value = matchObj.group(2)
	stats[measure] = value

	return ""

percents.sub(collectStat, GetWebPage(config["cobertura"]))
data = SaveUpdates("cobertura", stats)

page = GetTemplate("coverage")
page = FillTemplate(page, {"##COVERAGECHART##": MakeWikiProgressChart(data)})

WriteFile("temp.tmp", page)
GetWiki({"action": "storePage", "space": config["personal_space"], "title": "Code Coverage", "file": "temp.tmp", "parent": config["parent_page"]})
os.remove("temp.tmp")
