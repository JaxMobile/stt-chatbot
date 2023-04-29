import logging
from getpass import getpass
from argparse import ArgumentParser

import slixmpp



class EchoBot(slixmpp.ClientXMPP):

    """
    A simple Slixmpp bot that will echo messages it
    receives, along with a short thank you message.
    """

    def __init__(self, jid, password, sasl_mech, plugin_config):

      slixmpp.ClientXMPP.__init__(self, jid, password, sasl_mech=sasl_mech, plugin_config= plugin_config)
      

      self.register_plugin('xep_0030') # Service Discovery
      self.register_plugin('xep_0004') # Data Forms
      self.register_plugin('xep_0060') # PubSub
      self.register_plugin('xep_0199') # XMPP Ping

      self.add_event_handler("session_start", self.start)
      self.add_event_handler("message", self.message)


      self.register_plugin('MediaProcessPlugin', module="extension.oob.oob")
      
    def oob_handler(self):
        print("OOB_handler detected")

    async def start(self, event):
        self.send_presence()
        await self.get_roster()

    def message(self, msg):
        if msg['type'] in ('chat', 'normal'):
            msg.reply("Thanks for sending\n%(body)s" % msg).send()


if __name__ == '__main__':
    # Setup the command line arguments.
    parser = ArgumentParser(description=EchoBot.__doc__)

    # Output verbosity options.
    parser.add_argument("-q", "--quiet", help="set logging to ERROR",
                        action="store_const", dest="loglevel",
                        const=logging.ERROR, default=logging.INFO)
    parser.add_argument("-d", "--debug", help="set logging to DEBUG",
                        action="store_const", dest="loglevel",
                        const=logging.DEBUG, default=logging.INFO)

    # JID and password options.
    parser.add_argument("-j", "--jid", dest="jid",
                        help="JID to use")
    parser.add_argument("-p", "--password", dest="password",
                        help="password to use")

    args = parser.parse_args()

    # Setup logging.
    logging.basicConfig(level=args.loglevel,
                        format='%(levelname)-8s %(message)s')

    if args.jid is None:
        args.jid = "chatbot@localhost"
    if args.password is None:
        args.password = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJleHAiOjE2ODc4NzIxMTYsImlhdCI6MTY3Nzg2NzMxNywidW5hbWUiOiJjaGF0Ym90In0.P9Tha-h3BoRi6rZq3HW2oVTErRg8CETezwZKjy3gquA"

    plugin_config = {
      'feature_mechanisms': {
        'unencrypted_plain': True,
      }
    }
    xmpp = EchoBot(args.jid, args.password, 'PLAIN', plugin_config)


    

    # Connect to the XMPP server and start processing XMPP stanzas.
    xmpp.connect(address=["localhost",5222], force_starttls= False,disable_starttls=True)
    xmpp.process()