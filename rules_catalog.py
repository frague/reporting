import os
import glob
import libxml2
from rabbithole import *

ProfileNeeded()

path = "D:/dev/BigRock/rep/rules/new_storage"
types = {"provider": "Provider", "template": "Template", "aggregation": "Aggregation", "xref": "XREF", "conditional": "Conditional"}
typeTemplate = GetTemplate("rule_type")
lineTemplate = GetTemplate("rule_line")
emptySpaces = re.compile("[ \t\n\r]+")
prd = re.compile("PRD: (\d(\.\d+)+)")
useInFilterExpr = re.compile("/useinfilter=[\"\']{0,1}true[\"\']{0,1}/", re.IGNORECASE)

result = {}

def ProcessTags(tags):
	return ", ".join([tag.content.replace("*", "\\*") for tag in tags])

def ProcessRule(file):
	mtime = time.strftime("%Y-%m-%d,&nbsp;%H:%M", time.localtime(os.path.getmtime(file)))
 
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

	
	useInFilter = "both"
	if doc.getRootElement().name == "provider" and doc.getRootElement().prop("useInFilter") != "true":
		useInFilter = "recommend"

#	print "%s -> %s" % (doc.getRootElement().name, useInFilter)

	comment = ""
	match = prd.search(description)
	if match:
		comment = match.group(1)
	description = prd.sub("", description)

	AppendSubSet(result, type, FillTemplate(lineTemplate, {"##NAME##": name, "##DESCRIPTION##": description, "##GOAL##": ProcessTags(tags), "##PRD##": comment, "##UPDATED##": mtime, "##URI##": os.path.basename(file), "##USEINFILTER##": useInFilter}))


[ProcessRule(file) for file in glob.glob(os.path.join(path, "*.*"))]


WriteFile("rules_cat.tmp", "{table:class=confluenceTable}%s{table}" % "".join([FillTemplate(typeTemplate, {"##TYPE##": types[type], "##RULES##": "".join(result[type])}) for type in result.keys()]))
GetWiki({"action": "storePage", "space": config["personal_space"], "title": "Rules Catalog (generated)", "file": "rules_cat.tmp", "parent": "Home"})
os.remove("rules_cat.tmp")
