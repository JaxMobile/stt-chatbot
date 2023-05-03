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

import urlextract
import re
from Bio import Align
import functools

from chatbot.whisper.model import run_asr
from chatbot.plugins.audio_bot.stanza import AudioBot, AudioBotReq
import mimetypes





class AudioBotPlugin(BasePlugin):
    """
    This plugin is used to create langex audio transcript chatbot
    """
    name = 'AudioBotPlugin'
    description = 'AudioBotPlugin based on xep_0066'
    dependencies = {'xep_0030', 'xep_0066'}
    assess_list = [[0, "You must be a newbie with this english"], [0.3, "You need to practice more :(("], [0.5, "Not very bad, you have some errors"], [0.9, "You are good. A little bit to be perfect"], [1, "Perfect!! You have no error in your pronunciation"]]
    
    supported_commands = {
      "pronunc_assess": {
        "language": ['af', 'am', 'ar', 'as', 'az', 'ba', 'be', 'bg', 'bn', 'bo', 'br', 'bs', 'ca', 'cs', 'cy', 'da', 'de', 'el', 'en', 'es', 'et', 'eu', 'fa', 'fi', 'fo', 'fr', 'gl', 'gu', 'ha', 'haw', 'he', 'hi', 'hr', 'ht', 'hu', 'hy', 'id', 'is', 'it', 'ja', 'jw', 'ka', 'kk', 'km', 'kn', 'ko', 'la', 'lb', 'ln', 'lo', 'lt', 'lv', 'mg', 'mi', 'mk', 'ml', 'mn', 'mr', 'ms', 'mt', 'my', 'ne', 'nl', 'nn', 'no', 'oc', 'pa', 'pl', 'ps', 'pt', 'ro', 'ru', 'sa', 'sd', 'si', 'sk', 'sl', 'sn', 'so', 'sq', 'sr', 'su', 'sv', 'sw', 'ta', 'te', 'tg', 'th', 'tk', 'tl', 'tr', 'tt', 'uk', 'ur', 'uz', 'vi', 'yi', 'yo', 'zh', 'Afrikaans', 'Albanian', 'Amharic', 'Arabic', 'Armenian', 'Assamese', 'Azerbaijani', 'Bashkir', 'Basque', 'Belarusian', 'Bengali', 'Bosnian', 'Breton', 'Bulgarian', 'Burmese', 'Castilian', 'Catalan', 'Chinese', 'Croatian', 'Czech', 'Danish', 'Dutch', 'English', 'Estonian', 'Faroese', 'Finnish', 'Flemish', 'French', 'Galician', 'Georgian', 'German', 'Greek', 'Gujarati', 'Haitian', 'Haitian Creole', 'Hausa', 'Hawaiian', 'Hebrew', 'Hindi', 'Hungarian', 'Icelandic', 'Indonesian', 'Italian', 'Japanese', 'Javanese', 'Kannada', 'Kazakh', 'Khmer', 'Korean', 'Lao', 'Latin', 'Latvian', 'Letzeburgesch', 'Lingala', 'Lithuanian', 'Luxembourgish', 'Macedonian', 'Malagasy', 'Malay', 'Malayalam', 'Maltese', 'Maori', 'Marathi', 'Moldavian', 'Moldovan', 'Mongolian', 'Myanmar', 'Nepali', 'Norwegian', 'Nynorsk', 'Occitan', 'Panjabi', 'Pashto', 'Persian', 'Polish', 'Portuguese', 'Punjabi', 'Pushto', 'Romanian', 'Russian', 'Sanskrit', 'Serbian', 'Shona', 'Sindhi', 'Sinhala', 'Sinhalese', 'Slovak', 'Slovenian', 'Somali', 'Spanish', 'Sundanese', 'Swahili', 'Swedish', 'Tagalog', 'Tajik', 'Tamil', 'Tatar', 'Telugu', 'Thai', 'Tibetan', 'Turkish', 'Turkmen', 'Ukrainian', 'Urdu', 'Uzbek', 'Valencian', 'Vietnamese', 'Welsh', 'Yiddish', 'Yoruba']
      }
      , 

      "vocab_schedule": []
    }


    
    def plugin_init(self):
        self.xmpp.register_handler(
            Callback('AudioBotRequest',
                     MatchXPath('{%s}message/body' % (self.xmpp.default_ns)),
                     self.handleLangexChatBotMessage
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


    def cal_accuracy_per(self, accuracy_list):
      crr_count = functools.reduce(lambda x,y: x +1 if y[1]==True else x, accuracy_list, 0)
      return crr_count/len(accuracy_list)


    def parseCommand(self, msg_text):
      """
        Command syntax: [command][_{op1}]*: input
      """
      semi_sep_list = msg_text.split(":")
      command = ""
      opts = None
      if msg_text.startswith("!") and len(semi_sep_list) >=1:
        command_opts = semi_sep_list[0] #Get command and options

        regex = r'^([a-zA-Z_]+)((\*[a-zA-Z_]+)*)$'
        match = re.search(regex, command_opts[1:])
        if match:
          command = match.group(1)
          if not match.group(2):
            opts = []
          else:
            opts = match.group(2)[1:].split("*")

      if not command:
        return "pronunc_assess", [], msg_text, ""  #Treat all string as sample that gonna assess
      
      if command not in self.supported_commands:
        return None, [], "", "Sorry, I have not supported the command {}".format(command)
      
      body = "".join(semi_sep_list[1:])
    
      return command, opts, body, ""


    def handleLangexChatBotMessage(self, msg_stanza):
      msg_text =  self.extract_text(msg_stanza["body"]).strip()
      url = msg_stanza["oob"]["url"]
      if len(msg_text) <= 0:
        return self.xmpp.send_message(mto=msg_stanza["from"], mbody="I can not understand you if you don't input anything")

      command, opts, body, warning_msg = self.parseCommand(msg_text)

      if not command:
        return self.xmpp.send_message(mto=msg_stanza["from"], mbody=warning_msg)

      result = None
      if command == "pronunc_assess":
        result = self.handlePronuncAssessment(opts, url, body, msg_stanza["from"])

      else: 
        return self.xmpp.send_message(mto=msg_stanza["from"], mbody="Other commands have not been supported yet")

      self.sendMessageOnCommand(command, result, msg_stanza)
    

    def sendMessageOnCommand(self, command, result, msg_stanza):
      if command == "pronunc_assess":
        if result["status"] == 1:
          self.send_pronunc_peformance(result["origin_msg"], result["heard_msg"], result["acc_list"], result["language"], msg_stanza)
        elif result["status"] == 0:
          self.xmpp.send_message(mto=msg_stanza["from"], mbody=result["msg"])
          

    def handlePronuncAssessment(self, opts, url, body, userJid):
      """
      Return: 
        {
            "status": 1 if "success" else 0
            
            if status == 1:
              "heard_msg":
              "language":
              "acc_list":
              "origin_msg"
            else:
              "msg":
        }
      """

      mime_type, _ = mimetypes.guess_type(url)
      if not mime_type or (not mime_type.startswith("audio/") and not mime_type == "video/webm"):
        return {
          "status": 0,
          "msg": "Sorry, May be you missed your file or have sent invalid audio file. I can not perform the pronunciation assessment with text".format(body)
        }
      
      # Get target language of the user
      language = ""
      if not opts:
        # TODO: getTargetLanguage from database
        # self.getTargetLanguage(userJid)
        language = "en"
      else:
        language = opts[0]
      
      
      if language not in self.supported_commands["pronunc_assess"]["language"]:
        return {
          "status": 0,
          "msg": "Sorry, Your language has not supported to perform the assessment. Try: {}".format(self.supported_commands["pronunc_assess"]["language"])
        }
      
      response = requests.get(url, verify=False)
      audio_file = io.BytesIO(response.content)

      transcribe_result = run_asr(audio_file, "transcribe", language, method = "faster-whisper", encode = True)

      heard_msg = transcribe_result["text"]

      filter_msg = self.filter_seperator(body) # Filter origin text before matching
      filter_heard_msg = self.filter_seperator(heard_msg)
      
      match_coordinates = self.first_matched_coordinates(filter_msg, filter_heard_msg) # Find match coordinates between two string
      
      accuracy_list = self.get_pronunc_accuracy(match_coordinates, filter_msg, filter_heard_msg) # Get accuracy of word tokens

      return {
          "status": 1,
          "origin_msg": body,
          "heard_msg": heard_msg,
          "language": language,
          "acc_list": accuracy_list,
        }
      

    def transform2_match_str(self, accuracy_list, origin_input):
      pre_mindex_end = 0
      result_str = ""
      crr_list = list(filter(lambda x: x[1] == True, accuracy_list))
      for word, _ in crr_list:
        match = re.search(word, origin_input[pre_mindex_end:])
        
        mindex_start = pre_mindex_end + match.start()
        mindex_end = pre_mindex_end + match.end()
        result_str += (origin_input[pre_mindex_end : mindex_start]) 
        result_str +=("<g>{}</g>".format(origin_input[mindex_start:mindex_end]))

        pre_mindex_end = mindex_end
      
      result_str += origin_input[pre_mindex_end:]
      return result_str
                        
       
    def send_pronunc_peformance(self, origin_msg, heard_msg, accuracy_list, language, msg_stanza):
      # Send transcribe message
      message = "Pronunciation assessment in language: {}".format(language)
      message += "\nThis is what you said: "
      message += (heard_msg)
      
      crr_per = self.cal_accuracy_per(accuracy_list)
      match_str = self.transform2_match_str(accuracy_list, origin_msg)
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
      text_msg = url_msg
      for url in urls:
          text_msg = text_msg.replace(url, '')

      return text_msg
        