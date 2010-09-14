#!/usr/bin/python

from rabbithole import *


ProfileNeeded()


filename = "./cache/review_offset.txt"
re = config["reviewers"]
l = len(re)

page = GetTemplate("reviewers")
offset = int(ReadFile(filename)) + 1
if (offset % l) == 0:
	offset = offset + 1
WriteFile(filename, str(offset))

reviewers = ""
for i in range(0, l):
	reviewers += "| [~%s] | [~%s] |\n" % (re[i], re[(i + offset) % l])

print reviewers

print "--- Publishing to wiki"

WriteFile("temp.tmp", FillTemplate(page, {"##REVIEWERS##": reviewers, "##UPDATED##": today.strftime("%A, %d %B, %Y")}))
GetWiki({"action": "storePage", "space": config["project_space"], "title": config["reviewers_page"], "file": "temp.tmp"})
os.remove("temp.tmp")
