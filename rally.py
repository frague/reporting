from rabbithole import *
from suds.client import Client
from suds.xsd.doctor import ImportDoctor, Import
from suds.transport.http import HttpAuthenticated

#username=config["rally"]["user"], password=config["rally"]["password"]

t = HttpAuthenticated(username=config["rally"]["user"], password=config["rally"]["password"])

pm = urllib2.HTTPPasswordMgrWithDefaultRealm()
pm.add_password(None, config["rally_soap"], config["rally"]["user"], config["rally"]["password"])

t.handler = urllib2.HTTPBasicAuthHandler(pm) 
t.urlopener = urllib2.build_opener(t.handler) 

imp = Import("http://schemas.xmlsoap.org/soap/encoding/")
imp.filter.add("http://rallydev.com/webservice/v1_22/domain") 

doctor = ImportDoctor(imp)
client = Client(config["rally_soap"], doctor=doctor, transport=t, cache=None)




#print client.service.getCurrentSubscription()

data = client.service.query({"Project": "RAS"})
print data


#ns0:Workspace workspace, ns0:Project project, xs:boolean projectScopeUp, xs:boolean projectScopeDown, xs:string artifactType, xs:string query, xs:string order, xs:boolean fetch, xs:long start, xs:long pagesize,