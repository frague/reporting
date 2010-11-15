from rabbithole import *

ProfileNeeded()

# Populate template with received values
chunks = {"##TODAY##": today.strftime("%Y-%m-%d"), "##TOMORROW##": tomorrow.strftime("%Y-%m-%d"), "##ABBR##": config["project_abbr"]}
page = FillTemplate(GetTemplate(config["report_template"]), chunks)

wikiServer = xmlrpclib.ServerProxy(config["wiki_xmlrpc"])
wikiToken = wikiServer.confluence1.login(config["wiki"]["user"], config["wiki"]["password"])

SaveWikiPage(wikiServer, wikiToken, config["project_space"], "%s Daily Status Update" % today.strftime("%Y-%m-%d"), page)

print "Done."
