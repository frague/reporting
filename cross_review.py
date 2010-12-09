#!/usr/bin/python

from rabbithole import *


ProfileNeeded()


filename = "./cache/review_offset.txt"
re = config["reviewers"]
l = len(re)

template = GetTemplate("reviewers")
wn = int(today.strftime("%U"))

data = yaml.load(ReadFile(filename)) or {"week": 0, "offset": 0}
if data["week"] != wn:
	data["week"] = wn
	data["offset"] += 1
	if (data["offset"] % l) == 0:
		data["offset"] += 1
	WriteFile(filename, yaml.dump(data))

reviewers = ""
for i in range(0, l):
	reviewers += "| [~%s] | should review | [~%s] |\n" % (re[i], re[(i + data["offset"]) % l])

print reviewers

print "--- Publishing to wiki"

wikiServer = xmlrpclib.ServerProxy(config["wiki_xmlrpc"])
wikiToken = wikiServer.confluence1.login(config["wiki"]["user"], config["wiki"]["password"])

page = wikiServer.confluence1.getPage(wikiToken, config["project_space"], config["reviewers_page"])
page["content"] = FillTemplate(template, {"##REVIEWERS##": reviewers, "##UPDATED##": today.strftime("%A, %d %B, %Y")})
wikiServer.confluence1.updatePage(wikiToken, page, {"minorEdit": True})

print "Done."
