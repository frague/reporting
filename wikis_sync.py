from rabbithole import *

space = GetParameter("space")
if not space:
	print "[!] Usage: wikis_sync.py --space=WIKI_SPACE"
	exit(1)

	
localWikiServer = xmlrpclib.ServerProxy(config["wiki_xmlrpc"])
localWikiToken = localWikiServer.confluence1.login(config["wiki"]["user"], config["wiki"]["password"])

remoteWikiServer = xmlrpclib.ServerProxy("http://wiki2.arch.ebay.com/rpc/xmlrpc")
remoteWikiToken = remoteWikiServer.confluence1.login(config["wiki"]["user"], config["wiki"]["ebay_password"])

conf = yaml.load(ReadFile("conf/%s_wiki_sync.yaml" % space.lower()))
if not len(conf):
	print "[!] No config found!"
	exit(1)


pagesCache = {}

# Updates wiki page or creates the new one
def UpdateWikiPage(space, page_name, content, parent_page = ""):
	global remoteWikiServer, remoteWikiToken, pagesCache

	action = "+"

	try:
		# Getting existing page for update
		page = remoteWikiServer.confluence1.getPage(remoteWikiToken, space, page_name)
		page["content"] = content
		remoteWikiServer.confluence1.updatePage(remoteWikiToken, page, {"minorEdit": True, "versionComment": comment})
		action = "@"
	except:
		# New page
		page = {"title": page_name, "space": space, "content": content}
		if parent_page:
			if pagesCache.has_key(parent_page):
				parent = pagesCache[parent_page]
				page["parentId"] = parent["id"]
			else:
				try:
					parent = remoteWikiServer.confluence1.getPage(remoteWikiToken, space, parent_page)
					pagesCache[parent_page] = parent
					page["parentId"] = parent["id"]
				except:
					print "[!] Error getting parent page \"%s\" in space \"%s\"" % (parent_page, space)
					return False
		remoteWikiServer.confluence1.storePage(remoteWikiToken, page)

	print "[%s] Updated \"%s\" (%s)" % (action, page["title"], parent_page)
	return True


def SyncPage(page, parent_page):
	global localWikiToken, localWikiServer, remoteWikiServer, remoteWikiToken

	localPage = ""
	remotePage = ""
	try:
		localPage = localWikiServer.confluence1.getPage(localWikiToken, space, page)
		remotePage = remoteWikiServer.confluence1.getPage(remoteWikiToken, conf["destination_space"], page)
	except:
		pass

	try:
		localExists = localPage and int(localPage["id"]) > 0
		remoteExists = remotePage and int(remotePage["id"]) > 0
	except:
		print remotePage
		exit(1)


	img = ""
	if localExists:
		if re.search("\![^\!]{0,100}\.[a-zA-Z]{2,4}\!", localPage["content"]):
			img = " [IMG]"
		if re.search("\[\^[^\]]{0,100}\.[a-zA-Z]{2,4}\]", localPage["content"]):
			img += " [ATT]"

	if not remoteExists and localExists:
		UpdateWikiPage(conf["destination_space"], page, localPage["content"], parent_page)
	else:
		print "[ ]%s \"%s\"" % (img, page)

def SyncLayer(parent_page, pages):
	if not pages:
		return

	print "\n--- Parent: \"%s\"" % parent_page
	for page in pages.keys():
		SyncPage(page, parent_page)
		SyncLayer(page, pages[page])


SyncLayer(conf["root_page"], conf["pages"])	
