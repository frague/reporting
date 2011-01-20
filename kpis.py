#!/usr/bin/python

from rabbithole import *
from stats import *

ProfileNeeded()

wikiServer = xmlrpclib.ServerProxy(config["wiki_xmlrpc"])
wikiToken = wikiServer.confluence1.login(config["wiki"]["user"], config["wiki"]["password"])

for i in [TestsCoverage, PMDReport, FindBugsReport, TestsRunReport]:
	t = i(wikiServer, wikiToken)
	t.Run()
