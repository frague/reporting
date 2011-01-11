#!/usr/bin/python

from rabbithole import *

stats = {}
#percents = re.compile("<th align=\"left\">([^<]+)</th><td align=\"right\">(\d+)%</td>", re.MULTILINE)
percents = re.compile("<strong>([^<]+)</strong>[^&]*&nbsp;[^\d]*(\d+)%", re.MULTILINE)

def collectStat(matchObj):
	global stats

	measure = matchObj.group(1)
	value = matchObj.group(2)
	stats[measure] = value

	print "- %s = %s%%" % (measure, value)

	return ""


ProfileNeeded()

percents.sub(collectStat, GetWebPage(config["cobertura"]))
data = SaveUpdates(config["project_abbr"], "cobertura", stats)

headers = "|| "
columns = "| "
for key, value in sorted(stats.iteritems(), key=lambda (k,v): (v,k)):
	headers += "%s || " % key
	columns += "%s%% | " % value

content = FillTemplate(GetTemplate("coverage"), {"##UPDATED##": datetime.datetime.today().strftime("%b %d, %Y (%H:%M)"), "##HEADERS##": headers, "##COLUMNS##": columns, "##COVERAGECHART##": MakeWikiProgressChart(data)})
col = GetTemplate("coverage")

print "Publishing to wiki (with no notifications)"


wikiServer = xmlrpclib.ServerProxy(config["wiki_xmlrpc"])
wikiToken = wikiServer.confluence1.login(config["wiki"]["user"], config["wiki"]["password"])

page = wikiServer.confluence1.getPage(wikiToken, config["project_space"], "Code Coverage")
page["content"] = content
wikiServer.confluence1.updatePage(wikiToken, page, {"minorEdit": True})
