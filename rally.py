from rabbithole import *
from suds.client import Client
from suds.transport.http import HttpAuthenticated


t = HttpAuthenticated(username=config["rally"]["user"], password=config["rally"]["password"])
password_mgr = urllib2.HTTPPasswordMgrWithDefaultRealm()
password_mgr.add_password(None, config["rally_soap"], config["rally"]["user"], config["rally"]["password"])

t.handler = urllib2.HTTPBasicAuthHandler(password_mgr) 
t.urlopener = urllib2.build_opener(t.handler) 

client = Client(config["rally_soap"], transport=t)



data = client.service.query(ns0:Workspace workspace, ns0:Project project, xs:boolean projectScopeUp, xs:boolean projectScopeDown, xs:string artifactType, xs:string query, xs:string order, xs:boolean fetch, xs:long start, xs:long pagesize, )

print data

