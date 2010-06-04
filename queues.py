#!/usr/bin/python

from rabbithole import *

'''

<td>activemq.queue</td>
                <td colspan=2>Consumer.TORS.VirtualTopic.ODB_ALL</td>

'''

ProfileNeeded()

stats = {}
queueExpr = re.compile("<td>activemq.queue</td>[^<]*<td[^>]*>([^<]*)</td>", re.MULTILINE)

page = GetTemplate("queues_main")
lineTemplate = GetTemplate("queues_line")

used = {}

def GetDeployedQueue(url):
	global used

	print "Processing %s" % url
	match = None
	try:
		match = queueExpr.search(GetWebPage(url))
	except:
		return "_N/A_"

	if match:
		key = match.group(1)
		if used.has_key(key):
			key = "{color:red}%s{color}" % key
		used[key] = True
		return key

	return ""

print "--- Check if connected..."
try:
	GetWebPage(config["check_connection_url"])
except:
	print "[!] Not connected to VPN!"
	exit(0)


result = []
for env in config["deployments"].keys():
	url = "http://%s/info" % config["deployments"][env]
	result.append(FillTemplate(lineTemplate, {"##TITLE##": env, "##URL##": url, "##COMMENT##": GetDeployedQueue(url)}))
 

print "--- Publishing to wiki"

WriteFile("temp.tmp", FillTemplate(page, {"##QUEUES##": "".join(result), "##UPDATED##": today.strftime("%Y.%m.%d")}))
#GetWiki({"action": "storePage", "space": config["personal_space"], "title": "Code Coverage", "file": "temp.tmp", "parent": config["parent_page"]})
GetWiki({"action": "storePage", "space": config["project_space"], "title": "ActiveMQ queues utilization", "file": "temp.tmp"})
os.remove("temp.tmp")
