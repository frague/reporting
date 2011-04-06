#!/usr/bin/python

from rabbithole import *
from stats import *

ProfileNeeded()

wikiServer = xmlrpclib.ServerProxy(config["wiki_xmlrpc"])
wikiToken = wikiServer.confluence1.login(config["wiki"]["user"], config["wiki"]["password"])

def CreateReports(postfix=""):
	global wikiServer, wikiToken

	for i in [EmmaTestsCoverage, PMDReport, FindBugsReport, TestsRunReport]:
		t = i(wikiServer, wikiToken)
		if postfix:
			t.CacheName = "%s_%s" % (t.CacheName, postfix)
			t.PageName = "%s %s" % (t.PageName, postfix)
		t.Run()

CreateReports()

if config["sprintEnd"] == today:
	print "######################## Sprint has ended ########################"
	CreateReports("sprints")
	