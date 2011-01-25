#!/usr/bin/python

from rabbithole import *
from stats import *

ProfileNeeded()

wikiServer = xmlrpclib.ServerProxy(config["wiki_xmlrpc"])
wikiToken = wikiServer.confluence1.login(config["wiki"]["user"], config["wiki"]["password"])

def CreateReports(postfix=""):
	global wikiServer, wikiToken

	for i in [TestsCoverage, PMDReport, FindBugsReport, TestsRunReport]:
		t = i(wikiServer, wikiToken)
		t.CacheName += postfix
		t.Run()

print config["sprintEnd"] == today
exit(0)

CreateReports()

if config["sprintEnd"] == today:
	print "######################## Sprint has ended ########################"
	CreateReports("_sprint")
	