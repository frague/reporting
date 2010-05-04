#!/usr/bin/python
import warnings
warnings.simplefilter("ignore", DeprecationWarning)

from xmpp import *

############################################
## Handlers
def iqHandler(conn, iq_node):
    # Handler for processing some "get" query from custom namespace
    reply = iq_node.buildReply('result')
    # ... put some content into reply node
    conn.send(reply)
    raise NodeProcessed  # This stanza is fully processed

def presenceHandler(conn, presence_node): pass

def messageHandler(conn, mess_node): pass

	
class Jabber:
	client = None
	Name = "Jabber"

	def __init__(self):
		# Connecting to specified IP address.
		# Connecting to port 5223 - TLS is pre-started.
		# Using direct connect.

		jab = config["jabber"]

		# Create a client
		self.client = Client('griddynamics.com', debug=[])

		# Connect it to SSL port directly
		if not self.client.connect(server=(jab["server"], jab["port"])):
		    raise IOError('Can not connect to server.')

		# Authorize client
		if not self.client.auth(jab["login"], jab["password"], "big-bot"):
		    raise IOError('Can not auth with server.')

		# Register some handlers (if you will register them before auth they will be thrown away)
		self.client.RegisterHandler('presence',presenceHandler)
		self.client.RegisterHandler('iq',iqHandler)
		self.client.RegisterHandler('message',messageHandler)

		# Become available
		self.client.sendInitPresence()

		# Work some time
		self.client.Process(1)

	## Sends message
	def SendMessage(self, to, text):
		# If connection is brocken - restore it
		if not self.client.isConnected(): 
			self.client.reconnectAndReauth()

		# ...send an ASCII message
		self.client.send(Message(to, text))

		# ...work some more time - collect replies
		self.client.Process(1)

	## Disconnect
	def Disconnect(self):
		# ...and then disconnect.
		self.client.disconnect()

