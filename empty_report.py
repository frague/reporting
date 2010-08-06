from rabbithole import *

ProfileNeeded()

# Populate template with received values
chunks = {"##TODAY##": today.strftime("%Y-%m-%d"), "##TOMORROW##": tomorrow.strftime("%Y-%m-%d"), "##ABBR##": config["project_abbr"]}
page = FillTemplate(GetTemplate(config["report_template"]), chunks)

WriteFile("temp1.tmp", page)
#GetWiki({"action": "storePage", "space": config["personal_space"], "title": "gitlog + %s report template" % today, "file": "temp1.tmp", "parent": config["parent_page"]})
GetWiki({"action": "storeNews", "space": config["project_space"], "title": "%s Daily Status Update" % today.strftime("%Y-%m-%d"), "file": "temp1.tmp"})
os.remove("temp1.tmp")

print "Done"
