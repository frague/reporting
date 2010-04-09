import os
import glob
import libxml2
from rabbithole import *

path = "D:/dev/BigRock/rep/rules/new_storage"
types = {"provider": "Provider", "template": "Template", "aggregation": "Aggregation", "xref": "XREF", "conditional": "Conditional"}
typeTemplate = GetTemplate("rule_type")
lineTemplate = GetTemplate("rule_line")
emptySpaces = re.compile("[ \t\n\r]+")

result = {}

def ProcessTags(tags):
	return ", ".join([tag.content.replace("*", "\\*") for tag in tags])

def ProcessRule(file):
	doc = libxml2.parseFile(file)
	context = doc.xpathNewContext()

	isRule = False
	for type in types.keys():
		if len(context.xpathEval("//%s" % type)) == 1:
			isRule = True
			break

	if not isRule:
		return

	name = context.xpathEval("//name")[0].content
	description = emptySpaces.sub(" ", context.xpathEval("//description")[0].content).replace("->", "&rarr;")
	tags = context.xpathEval("//tag")

	comment = ""
	comments = context.xpathEval("//comment")
	if len(comments) > 0:
		comment = comments[0].content

	AppendSubSet(result, type, FillTemplate(lineTemplate, {"##NAME##": name, "##DESCRIPTION##": description, "##GOAL##": ProcessTags(tags), "##PRD##": comment}))


[ProcessRule(file) for file in glob.glob(os.path.join(path, "*.*"))]


WriteFile("rules_cat.tmp", "".join([FillTemplate(typeTemplate, {"##TYPE##": types[type], "##RULES##": "".join(result[type])}) for type in result.keys()]))
GetWiki({"action": "storePage", "space": config["personal_space"], "title": "Rules Catalog (generated)", "file": "rules_cat.tmp", "parent": "Home"})
os.remove("rules_cat.tmp")
