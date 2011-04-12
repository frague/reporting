from rabbithole import *



######################################################################################
# Getting data from external sources (Hudson) and publishing them

class ExternalData:
	# Abstract class
	global config

	def __init__(self, wikiServer, wikiToken):
		self.wikiServer = wikiServer
		self.wikiToken = wikiToken
		self.PostFix = ""
		self.ChartAdd = ""
		self.Order = []
		self.Init()

	def Init(self):
		pass
	
	def FetchData(self):
		print "(!) No fetching logic is defined!"
		return {}

	def GetLastValues(self, data):
		return data[sorted(data.keys(), reverse=True)[0]]

	def BuildLastValuesTable(self, data):
		headers = "|| "
		columns = "| "
		lastValues = self.GetLastValues(data)
#		for key, value in sorted(lastValues.iteritems(), key=lambda (k,v): (v,k)):
		keys = self.Order or sorted(lastValues.keys())
		for key in keys:
			headers += "%s || " % key
			columns += "%s%s | " % (lastValues[key], self.PostFix)
		print "(i) Last values: %s" % lastValues
		return "%s\n%s" % (headers, columns)

   	def MakeContent(self, data):
		print "(!) Updating wiki %s report page (with no notification)" % self.PageName
		return FillTemplate(GetTemplate(self.Template), {"##UPDATED##": datetime.datetime.today().strftime("%b %d, %Y (%H:%M)"), "##LASTVALUES##": self.BuildLastValuesTable(data), "##CHART##": MakeWikiProgressChart(data, self.ChartAdd, self.Order)})

	def UpdatePage(self, content):
#		print "[x] Saving is disabled for now...\n"
#		return

		if not self.PageName:
			print "(!) No page name is set!"
			return

		page = self.wikiServer.confluence1.getPage(self.wikiToken, config["project_space"], self.PageName)
		page["content"] = content
		self.wikiServer.confluence1.updatePage(self.wikiToken, page, {"minorEdit": True})

		print "(i) Page %s has been updated." % self.PageName

	def Run(self):
		print "======= Running %s report creation ==========================================" % self.PageName
		data = self.FetchData()
		if not data:
			print "(!) Data fetching error - exiting!"
			return

		self.UpdatePage(self.MakeContent(data))
		print "\n"


######################################################################################
# Code coverage w/ tests (Cobertura-based)

class CoberturaTestsCoverage(ExternalData):
	def Init(self):
		self.Url = config["cobertura"]
		self.Template = "coverage"
		self.PageName = "Cobertura Code Coverage"
		self.CacheName = "cobertura"
		self.PostFix = "%"
		self.ChartAdd = "\n\n|| Day || ||\n| %s | 100 |" % MakeChartDate(datetime.date.today())

	def collectStat(self, matchObj):
		measure = matchObj.group(1)
		value = matchObj.group(2)
		self.stats[measure] = value

		#print "- %s = %s%%" % (measure, value)
		return ""

	def FetchData(self):
		self.stats = {}
		percents = re.compile("<strong>([^<]+)</strong>[^&]*&nbsp;[^\d]*(\d+)%", re.MULTILINE)

		percents.sub(self.collectStat, WgetPage(self.Url))
		return SaveUpdates(config["project_abbr"], self.CacheName, self.stats)

######################################################################################
# Code coverage w/ tests (Emma-based)

class EmmaTestsCoverage(ExternalData):
	def Init(self):
		self.Url = config["emma"]
		self.Template = "emma_coverage"
		self.PageName = "Emma Code Coverage"
		self.CacheName = "emma"
		self.PostFix = "%"
		self.ChartAdd = "\n\n|| Day || ||\n| %s | 100 |" % MakeChartDate(datetime.date.today())

	def collectStat(self, k, v):
		self.stats[k] = v

		#print "- %s = %s%%" % (k, v)
		return ""

	def FetchData(self):
		self.stats = {}
		columnsExpr = re.compile("<th>name</th><th>(" + NotEqualExpression("</tr>") + "+)</tr>", re.MULTILINE)
		valuesExpr = re.compile("<td>all classes</td>([^\|]+)</tr></table><h3>Coverage Breakdown by Package", re.MULTILINE)
		valueExpr = re.compile("data='([^']+)'")
		
		page = WgetPage(self.Url)
		
		names = [DeTag(n) for n in GetMatchGroup(page, columnsExpr, 1).split("<th>")]

		text = GetMatchGroup(page, valuesExpr, 1)

		values = ["%3.2f" % float(v.group(1)) for v in re.finditer(valueExpr, text)]

		print names
		print values

		if len(names) == 0 or len(names) != len(values):
			return False
		
		for i in range(len(names)):
			self.collectStat(names[i], values[i])

		return SaveUpdates(config["project_abbr"], self.CacheName, self.stats)


######################################################################################
# Hudson standard report table

class HudsonReport(ExternalData):
	def FetchData(self):
		markup = GetMatchGroup(WgetPage(self.Url), re.compile("<table[^>]*id=\"analysis\.summary\"[^>]*>(([^<]|<[^/]|</[^t]|</t[^a])+)</table>"), 1)

		if not markup:
			return False

		stats = ParseHeadedTable(markup, True)
		return SaveUpdates(config["project_abbr"], self.CacheName, stats[0])



######################################################################################
# Code coverage w/ tests (Cobertura-based)

class PMDReport(HudsonReport):
	def Init(self):
		self.Url = config["pmd"]
		self.Template = "pmd"
		self.PageName = "PMD"
		self.CacheName = "pmd"
		self.Order = ["High Priority", "Normal Priority", "Low Priority", "Total"]


######################################################################################
# Code coverage w/ tests (Cobertura-based)

class FindBugsReport(HudsonReport):
	def Init(self):
		self.Url = config["findbugs"]
		self.Template = "findbugs"
		self.PageName = "FindBugs"
		self.CacheName = "findbugs"
		self.Order = ["High Priority", "Normal Priority", "Low Priority", "Total"]


######################################################################################
# Code coverage w/ tests (Log-based)

class TestsRunReport(ExternalData):
	def Init(self):
		self.Url = config["cobertura_log"]
		self.Template = "tests"
		self.PageName = "Tests Run"
		self.CacheName = "tests"
		self.Order = ["Errors", "Failures", "Skipped", "Tests run"]

	def collectTests(self, matchObj):
		self.tests["Tests run"] += int(matchObj.group(1))
		self.tests["Failures"] += int(matchObj.group(2))
		self.tests["Errors"] += int(matchObj.group(3))
		self.tests["Skipped"] += int(matchObj.group(4))
		return ""

	def FetchData(self):
		resultsExpr = re.compile("\nResults :\n\nTests run: (\d+), Failures: (\d+), Errors: (\d+), Skipped: (\d+)", re.MULTILINE)
		self.tests = {"Tests run": 0, "Failures": 0, "Errors": 0, "Skipped": 0}

		resultsExpr.sub(self.collectTests, WgetPage(self.Url))
		return SaveUpdates(config["project_abbr"], self.CacheName, self.tests)

