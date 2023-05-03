from slixmpp.xmlstream import ElementBase

class AudioBotReq(ElementBase):

    """
    """

    name = 'request'
    namespace = 'langex:audiobot'
    plugin_attrib = 'aud_crr_req'

class AudioBot(ElementBase):

    """
    """

    name = 'audiobot'
    namespace = 'langex:audiobot'
    plugin_attrib = 'audi_crr'