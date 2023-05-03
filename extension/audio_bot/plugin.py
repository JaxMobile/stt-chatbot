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
import requests
import io 
from whisper_langex.model import run_asr
import urlextract
import re
from Bio import Align
import functools

from extension.audio_bot.stanza import AudioBot, AudioBotReq





class AudioBotPlugin(BasePlugin):
    """
    This plugin is used to create langex audio transcript chatbot
    """
    name = 'AudioBotPlugin'
    description = 'AudioBotPlugin based on xep_0066'
    dependencies = {'xep_0030', 'xep_0066'}
    assess_list = [[0, "You must be a newbie with this english"], [0.3, "You need to practice more :(("], [0.5, "Not very bad, you have some errors"], [0.9, "You are good. A little bit to be perfect"], [1, "Perfect!! You have no error in your pronunciation"]]

    def plugin_init(self):
        self.xmpp.register_handler(
            Callback('AudioBotRequest',
                     MatchXPath('{%s}message/{%s}%s' % (self.xmpp.default_ns, OOB.namespace, OOB.name)),
                     self.__handleAudioBotRequest
                     ))
        
        register_stanza_plugin(Message, AudioBot)
        register_stanza_plugin(Message, AudioBotReq)
        register_stanza_plugin(Message, OOB)

    def post_init(self):
      BasePlugin.post_init(self)

      self.aligner = Align.PairwiseAligner()
      self.aligner.open_gap_score = -0.5
      self.aligner.extend_gap_score = -0.1
      self.aligner.target_end_gap_score = 0.0
      self.aligner.query_end_gap_score = 0.0



    def __handleAudioBotRequest(self, message):
      if not message["oob"]["url"]:
        return self.audioFileNotExistResponse(self, message)
      
      response = requests.get(message["oob"]["url"], verify=False)
      audio_file = io.BytesIO(response.content)

      transcribe_result = run_asr(audio_file, "transcribe", "en", method = "openai-whisper", encode = True)

      self.msg_text =  self.extract_text(message["body"])
      self.heard_text = transcribe_result["text"]

      filter_msg_text = self.filter_seperator(self.msg_text) # Filter origin text before matching
      filter_heard_text = self.filter_seperator(self.heard_text)

      match_coordinates = self.first_matched_coordinates(filter_msg_text, filter_heard_text) # Find match coordinates between two string
      
      accuracy_list = self.get_pronunc_accuracy(match_coordinates, filter_msg_text, filter_heard_text) # Get accuracy of word tokens

      self.send_pronunc_peformance(accuracy_list, message)


    def audioFileNotExistResponse(self, message_stanza):
      message = "You are not sending any audio file to be corrected"
      self.xmpp.send_message(mto=message_stanza["from"], mbody=message)


    def cal_accuracy_per(self, accuracy_list):
      crr_count = functools.reduce(lambda x,y: x +1 if y[1]==True else x, accuracy_list, 0)
      return crr_count/len(accuracy_list)
    
    
    def transform2_match_str(self, accuracy_list):
      pre_mindex_end = 0
      result_str = ""
      crr_list = list(filter(lambda x: x[1] == True, accuracy_list))
      for word, _ in crr_list:
        match = re.search(word, self.msg_text[pre_mindex_end:])
        
        mindex_start = pre_mindex_end + match.start()
        mindex_end = pre_mindex_end + match.end()
        result_str += (self.msg_text[pre_mindex_end : mindex_start]) 
        result_str +=("<g>{}</g>".format(self.msg_text[mindex_start:mindex_end]))

        pre_mindex_end = mindex_end
      
      result_str += self.msg_text[pre_mindex_end:]
      return result_str
                        
       
    def send_pronunc_peformance(self, accuracy_list, msg_stanza):
      # Send transcribe message
      message = "I have listened you said this:  "
      message += (self.heard_text)
      
      crr_per = self.cal_accuracy_per(accuracy_list)
      match_str = self.transform2_match_str(accuracy_list)
      for assess_pnt, eval in self.assess_list[::-1]:
         if crr_per >= assess_pnt:
            message += ("\n{}, your score is {}, this is how your voice match: {}".format(eval, crr_per, match_str))
            break
      

      send_msg = self.xmpp.make_message(mto = msg_stanza["from"], mbody = message, mtype=msg_stanza["type"], mfrom=self.xmpp.jid)
      send_msg.append(AudioBot())

      send_msg.send()
      
      

    def get_pronunc_accuracy(self, coordinates, input_str, trans_str):
      pre_mati1, pre_mati2 = 0, 0
      path = list(zip(coordinates[0], coordinates[1]))
      align_input_str, align_trans_str = "", ""

      for mati1, mati2 in path[1:]:
        if pre_mati1 < mati1:
          align_input_str += input_str[pre_mati1:mati1]
        if pre_mati2 < mati2:
          align_trans_str += trans_str[pre_mati2:mati2]
        if pre_mati1 == mati1:
          align_input_str += "-"*(mati2 -pre_mati2)
        if pre_mati2 == mati2:
          align_trans_str += "-"*(mati1 -pre_mati1)
        pre_mati1, pre_mati2 = mati1, mati2
      
      accuracy_list = []
      word_findex = 0
      eostr = False
      for index, char in enumerate(align_input_str):
        if index == len(align_input_str)-1:
          eostr= True
          index = index + 1
        if char == " " or eostr:
          if(align_input_str[word_findex:index].lower() == align_trans_str[word_findex:index].lower()):
            accuracy_list.append([align_input_str[word_findex:index], True])
          else:
            accuracy_list.append([align_input_str[word_findex:index], False])
          word_findex = index + 1
      
      return accuracy_list

  
    def first_matched_coordinates(self, str1, str2):
      alignments = self.aligner.align(str1, str2)
      return alignments[0].coordinates
  
    def filter_seperator(self, str):

      letter_pattern = re.compile('[^\W\d_ ]+', re.UNICODE)
      letters_only = ' '.join(letter_pattern.findall(str))

      return letters_only


    def extract_text(self, url_msg):
      extractor = urlextract.URLExtract()
      urls = extractor.find_urls(url_msg)
      text_msg = ""
      for url in urls:
          text_msg = url_msg.replace(url, '')

      return text_msg
        