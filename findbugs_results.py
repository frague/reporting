#!/usr/bin/python

from rabbithole import *


#<table id="analysis.summary" class="pane"><tbody><tr><td class="pane-header">Total</td><td class="pane-header">High Priority</td><td class="pane-header">Normal Priority</td><td class="pane-header">Low Priority</td></tr></tbody><tbody><tr><td class="pane">126</td><td class="pane"><a href="HIGH">10</a></td><td class="pane"><a href="NORMAL">116</a></td><td class="pane">
#              0
#            </td></tr></tbody></table>

ProfileNeeded()

os.system("wget %s -O findbugs" % config["findbugs"])
markup = GetMatchGroup(ReadFile("findbugs"), re.compile("<table[^>]*id=\"analysis\.summary\"[^>]*>(([^<]|<[^/]|</[^t]|</t[^a])+)</table>"), 1)
os.remove("findbugs")

if not markup:
	print "[!] Parsing error!"
	exit(0)

stats = ParseHeadedTable(markup, True)

data = SaveUpdates(config["project_abbr"], "findbugs", stats[0])
print stats[0]

content = FillTemplate(GetTemplate("findbugs"), {"##UPDATED##": datetime.datetime.today().strftime("%b %d, %Y (%H:%M)"), "##FINDBUGSCHART##": MakeWikiProgressChart(data)})

print "Publishing to wiki (with no notifications)"


wikiServer = xmlrpclib.ServerProxy(config["wiki_xmlrpc"])
wikiToken = wikiServer.confluence1.login(config["wiki"]["user"], config["wiki"]["password"])

page = wikiServer.confluence1.getPage(wikiToken, config["project_space"], "FindBugs")
page["content"] = content
wikiServer.confluence1.updatePage(wikiToken, page, {"minorEdit": True})

