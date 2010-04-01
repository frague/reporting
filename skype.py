#!/usr/bin/python
import Skype4Py

# attach our program to the Skype
class Skype:
	instance = None
	Name = "Skype"

	def __init__(self):
		# create Skype object
		self.instance = Skype4Py.Skype()
		self.instance.OnAttachmentStatus = self.OnAttach

		if not self.instance.Client.IsRunning:
			print 'Skype: Starting...'
			self.instance.Client.Start()

	def OnAttach(self, status):
		#print "Skype: API attachment status: %s" % self.instance.Convert.AttachmentStatusToText(status)
		if status == Skype4Py.apiAttachAvailable:
			self.instance.Attach()

	def SendMessage(self, to, text):
		if not self.instance:
			return 

		# get the name of Skype contact from the command line and create an object uprofile
		uprofile = self.instance.User(Username=to)

		# now we can use all the methods from this object (see the documentations for "IUser" class for all available methods)
		# print the full name of a person
		#print 'profile: ' + uprofile.FullName

		# open chat with uname
		uchat = self.instance.CreateChatWith(to)
		uchat.SendMessage(text)
		print 'Skype: message sent to %s (%s)' % (to, uprofile.FullName)

	def Disconnect(self): pass
