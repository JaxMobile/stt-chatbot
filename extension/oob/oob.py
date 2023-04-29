"""
Creating a Slixmpp Plugin

This is a minimal implementation of XEP-0077 to serve
as a tutorial for creating Slixmpp plugins.
"""

from slixmpp.plugins.base import BasePlugin
from slixmpp.xmlstream.handler.callback import Callback
from slixmpp.xmlstream.matcher.xpath import MatchXPath
from slixmpp.xmlstream import ElementBase, ET, JID, register_stanza_plugin
from slixmpp.stanza import Iq, Message
from slixmpp.plugins.xep_0066.stanza import OOB
import copy


# class Registration(ElementBase):
#     namespace = 'jabber:iq:register'
#     name = 'query'
#     plugin_attrib = 'register'
#     interfaces = {'username', 'password', 'email', 'nick', 'name',
#                   'first', 'last', 'address', 'city', 'state', 'zip',
#                   'phone', 'url', 'date', 'misc', 'text', 'key',
#                   'registered', 'remove', 'instructions'}
#     sub_interfaces = interfaces

#     def getRegistered(self):
#         present = self.xml.find('{%s}registered' % self.namespace)
#         return present is not None

#     def getRemove(self):
#         present = self.xml.find('{%s}remove' % self.namespace)
#         return present is not None

#     def setRegistered(self, registered):
#         if registered:
#             self.addField('registered')
#         else:
#             del self['registered']

#     def setRemove(self, remove):
#         if remove:
#             self.addField('remove')
#         else:
#             del self['remove']

#     def addField(self, name):
#         itemXML = ET.Element('{%s}%s' % (self.namespace, name))
#         self.xml.append(itemXML)


# class UserStore(object):
#     def __init__(self):
#         self.users = {}

#     def __getitem__(self, jid):
#         return self.users.get(jid, None)

#     def register(self, jid, registration):
#         username = registration['username']

#         def filter_usernames(user):
#             return user != jid and self.users[user]['username'] == username

#         conflicts = filter(filter_usernames, self.users.keys())
#         if conflicts:
#             return False

#         self.users[jid] = registration
#         return True

#     def unregister(self, jid):
#         del self.users[jid]

class MediaProcessPlugin(BasePlugin):
    """
    This plugin is used to create langex audio transcript chatbot
    """
    name = 'MediaProcessPlugin'
    description = 'langex_media_processing based on xep_0066'
    dependencies = {'xep_0030'}
    stanza = OOB

    def plugin_init(self):
        self.description = ""


        self.xmpp.register_handler(
            Callback('File-received',
                     MatchXPath('{%s}message/{%s}%s' % (self.xmpp.default_ns, OOB.namespace, OOB.name)),
                     self.__handleReceivingFile
                     ))
        
        register_stanza_plugin(Message, OOB)

    def post_init(self):
        BasePlugin.post_init(self)
        self.xmpp['xep_0030'].add_feature(OOB.namespace)

    def __handleReceivingFile(self, message):
        print(message["oob"]["url"])

    def setForm(self, *fields):
        self.form_fields = fields

    def setInstructions(self, instructions):
        self.form_instructions = instructions

    def sendRegistrationForm(self, iq, userData=None):
        reg = iq['register']
        if userData is None:
            userData = {}
        else:
            reg['registered'] = True

        if self.form_instructions:
            reg['instructions'] = self.form_instructions

        for field in self.form_fields:
            data = userData.get(field, '')
            if data:
                # Add field with existing data
                reg[field] = data
            else:
                # Add a blank field
                reg.addField(field)

        reply = iq.reply()
        reply.set_payload(reg.xml)
        reply.send()

    def _sendError(self, iq, code, error_type, name, text=''):
        reply = iq.reply()
        reply.set_payload(iq['register'].xml)
        reply.error()
        reply['error']['code'] = code
        reply['error']['type'] = error_type
        reply['error']['condition'] = name
        reply['error']['text'] = text
        reply.send()