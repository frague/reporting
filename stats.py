from rabbithole import *



######################################################################################
# Getting data from external sources (Hudson) and publishing them

class ExternalData:
	# Abstract class
	global config

	def __init__(self, wikiServer, wikiToken):
		self.wikiServer = wikiServer
		self.wikiToken = wikiToken
		self.Init()

	def Init(self):
		pass
	
	def WgetPage(self, url):
		name = str(uuid.uuid1())
		os.system("wget %s -O %s" % (url, name))
		result = ReadFile(name)
		os.remove(name)
		return result
		
	def FetchData(self):
		print "[!] No fetching logic is defined!"
		return {}

	def MakeContent(self, data):
		print "[!] No content formatting logic is defined!"
		return ""

	def UpdatePage(self, content):
#		print "[x] Saving is disabled for now...\n"
#		return

		if not self.PageName:
			print "[!] No page name is set!"
			return

		page = self.wikiServer.confluence1.getPage(self.wikiToken, config["project_space"], self.PageName)
		page["content"] = content
		self.wikiServer.confluence1.updatePage(self.wikiToken, page, {"minorEdit": True})

		print "[+] Page %s has been updated." % self.PageName

	def Run(self):
		print "======= Running %s report creation ==========================================" % self.PageName
		data = self.FetchData()
		if not data:
			print "[x] Data fetching error - exiting!"
			return

		self.UpdatePage(self.MakeContent(data))
		print "\n"


class HudsonReport(ExternalData):
   	def MakeContent(self, data):
		print "[+] Updating wiki %s report page (with no notification)" % self.PageName
		return FillTemplate(GetTemplate(self.Template), {"##UPDATED##": datetime.datetime.today().strftime("%b %d, %Y (%H:%M)"), "##CHART##": MakeWikiProgressChart(data)})


######################################################################################
# Code coverage w/ tests (Cobertura-based)

class TestsCoverage(ExternalData):
	def Init(self):
		self.Url = config["cobertura"]
		self.Template = "coverage"
		self.PageName = "Code Coverage"
		self.CacheName = "cobertura"

	def collectStat(self, matchObj):
		measure = matchObj.group(1)
		value = matchObj.group(2)
		self.stats[measure] = value

		print "- %s = %s%%" % (measure, value)
		return ""

	def FetchData(self):
		self.stats = {}
		percents = re.compile("<strong>([^<]+)</strong>[^&]*&nbsp;[^\d]*(\d+)%", re.MULTILINE)

		percents.sub(self.collectStat, self.WgetPage(self.Url))
		return SaveUpdates(config["project_abbr"], self.CacheName, self.stats)

	def MakeContent(self, data):
		headers = "|| "
		columns = "| "
		for key, value in sorted(data.iteritems(), key=lambda (k,v): (v,k)):
			headers += "%s || " % key
			columns += "%s%% | " % value

		print "[+] Updating wiki tests coverage page (with no notification)"

		return FillTemplate(GetTemplate(self.Template), {"##UPDATED##": datetime.datetime.today().strftime("%b %d, %Y (%H:%M)"), "##HEADERS##": headers, "##COLUMNS##": columns, "##COVERAGECHART##": MakeWikiProgressChart(data)})


######################################################################################
# Code coverage w/ tests (Cobertura-based)

class PMDReport(HudsonReport):
	def Init(self):
		self.Url = config["pmd"]
		self.Template = "pmd"
		self.PageName = "PMD"
		self.CacheName = "pmd"

	def FetchData(self):
		markup = GetMatchGroup(self.WgetPage(self.Url), re.compile("<table[^>]*id=\"analysis\.summary\"[^>]*>(([^<]|<[^/]|</[^t]|</t[^a])+)</table>"), 1)

		if not markup:
			return False

		stats = ParseHeadedTable(markup, True)

		print stats[0]

		return SaveUpdates(config["project_abbr"], self.CacheName, stats[0])


######################################################################################
# Code coverage w/ tests (Cobertura-based)

class FindBugsReport(HudsonReport):
	def Init(self):
		self.Url = config["findbugs"]
		self.Template = "findbugs"
		self.PageName = "FindBugs"
		self.CacheName = "findbugs"

	def FetchData(self):
		markup = GetMatchGroup(self.WgetPage(self.Url), re.compile("<table[^>]*id=\"analysis\.summary\"[^>]*>(([^<]|<[^/]|</[^t]|</t[^a])+)</table>"), 1)

		if not markup:
			return False

		stats = ParseHeadedTable(markup, True)
		print stats[0]
		return SaveUpdates(config["project_abbr"], self.CacheName, stats[0])


######################################################################################
# Code coverage w/ tests (Cobertura-based)

class TestsRunReport(HudsonReport):
	def Init(self):
		self.Url = config["cobertura_log"]
		self.Template = "tests"
		self.PageName = "Tests Run"
		self.CacheName = "tests"

	def collectTests(self, matchObj):
		self.tests["Tests run"] += int(matchObj.group(1))
		self.tests["Failures"] += int(matchObj.group(2))
		self.tests["Errors"] += int(matchObj.group(3))
		self.tests["Skipped"] += int(matchObj.group(4))
		return ""

	def FetchData(self):
		resultsExpr = re.compile("\nResults :\n\nTests run: (\d+), Failures: (\d+), Errors: (\d+), Skipped: (\d+)", re.MULTILINE)
		self.tests = {"Tests run": 0, "Failures": 0, "Errors": 0, "Skipped": 0}

		resultsExpr.sub(self.collectTests, self.WgetPage(self.Url))
		return SaveUpdates(config["project_abbr"], self.CacheName, self.tests)

