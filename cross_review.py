#!/usr/bin/python

from rabbithole import *


ProfileNeeded()


filename = "./cache/review_offset.txt"
re = config["reviewers"]
l = len(re)

page = GetTemplate("reviewers")
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


WriteFile("temp.tmp", FillTemplate(page, {"##REVIEWERS##": reviewers, "##UPDATED##": today.strftime("%A, %d %B, %Y")}))
GetWiki({"action": "storePage", "space": config["project_space"], "title": config["reviewers_page"], "file": "temp.tmp"})
os.remove("temp.tmp")
