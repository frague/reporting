#!/usr/bin/python

import libxml2
from rabbithole import *


print "--- Check if connected..."
try:
	GetWebPage(config["check_connection_url"])
except:
	print "[!] Not connected to VPN!"
	exit(0)

#############################################################################################################
## Getting queues consumers

url = GetParameter("url") or config["queues"]
if not url:
	print "[!] URL is not provided. Usage: queues_check.py --url=<Queues Page URL>"
	exit(0)


def GetQueuesByCondition(doc, condition, title):
	queues = [q.prop("name") for q in doc.xpathNewContext().xpathEval("//queue/stats[%s]/parent::*" % condition)]

	success = True
	print "\n--- %s:" % title
	for q in queues:
		if ours.search(q):
			print q
			success = False
	if success:
		print "None"
	return success


ours = re.compile("(tors|ras|cloud)", re.IGNORECASE)
keepTrying = True
while keepTrying:
	try:
		doc = libxml2.parseDoc(WgetPage(url))

		result = GetQueuesByCondition(doc, "@size>='20000'", "Queues w/ size > 20000 messages")
		result = result and GetQueuesByCondition(doc, "@consumerCount='0'", "Queues w/ zero consumers")

		keepTrying = False
	except:
		print "[!] Error parsing queues. Re-attempting in 5 seconds."
		time.sleep(5)


print "Done.\n\n"
if not result:
	exit(1)