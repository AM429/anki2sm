import cssutils
from typing import Dict, Union

from Caching.LRUCaching import DeckPagePool
from Rendering import Formatters, mustache
from Models import Card, Note
import premailer

from Utils.HtmlUtils import get_rule_for_selector

_RENDERED_CSS = {}


class CardRenderer(object):
	def __init__(self, anki_notes: Union[Dict[str, Note], DeckPagePool]):
		self.__AnkiNotes = anki_notes
	
	def __int__(self):
		pass
	
	def mock(self, cid, note_id, ordi: str):
		reqNote = self.__AnkiNotes[note_id]
		if reqNote is None:
			print("BRUH")
	
	def render(self, cid, note_id, ordi: str):
		reqNote = self.__AnkiNotes[note_id]
		if reqNote.model.type == 0:
			return self.__renderToNormalCard(cid, ordi, reqNote)
		elif reqNote.model.type == 1:
			return self.__renderToClozeCard(cid, ordi, reqNote)
	
	def render2(self,reqNote,cid, ordi: str):
		if reqNote.model.type == 0:
			return self.__renderToNormalCard(cid, ordi, reqNote)
		elif reqNote.model.type == 1:
			return self.__renderToClozeCard(cid, ordi, reqNote)
	
	def __renderToClozeCard(self, cid, ordi: str, reqNote: Note) -> Card:
		reqTemplate = self.__getTemplateofOrd(reqNote.model.tmpls, 0)
		mustache.filters["cloze"] = lambda txt: Formatters.cloze_q_filter(txt, str(int(ordi) + 1))
		
		if reqNote.model.id + str(ordi) in _RENDERED_CSS.keys():
			css = _RENDERED_CSS[reqNote.model.id + str(ordi)]
		else:
			css = cssutils.parseString(reqNote.model.css)
			css = self.__buildCssForOrd(css, ordi) if css else ""
			_RENDERED_CSS[reqNote.model.id + str(ordi)] = css
		
		questionTg = "<style> " + css + " </style><section class='card' style=\" height:100%; width:100%; margin:0; \">" \
		             + mustache.render(reqTemplate.qfmt, self.__buildStubbleDict(reqNote)) + "</section>"
		mustache.filters["cloze"] = lambda txt: Formatters.cloze_a_filter(txt, str(int(ordi) + 1))
		
		answerTag = "<section class='card' style=\" height:100%; width:100%; margin:0; \">" \
		            + mustache.render(reqTemplate.afmt, self.__buildStubbleDict(reqNote)) + "</section>"
		questionTg = premailer.transform(questionTg)
		answerTag = premailer.transform(answerTag)
		
		return Card(cid, questionTg, answerTag)
	
	def __renderToNormalCard(self, cid, ordi: str, reqNote: Note) -> Card:
		reqTemplate = self.__getTemplateofOrd(reqNote.model.tmpls, int(ordi))
		
		if reqNote.model.id + str(ordi) in _RENDERED_CSS.keys():
			css = _RENDERED_CSS[reqNote.model.id + str(ordi)]
		else:
			css = cssutils.parseString(reqNote.model.css)
			css = self.__buildCssForOrd(css, ordi) if css else ""
			_RENDERED_CSS[reqNote.model.id + str(ordi)] = css
		
		questionTg = "<style> " + css \
		             + "</style><section class='card' style=\" height:100%; width:100%; margin:0; \">" \
		             + mustache.render(reqTemplate.qfmt, self.__buildStubbleDict(reqNote)) + "</section>"
		answerTag = "<style> " + css \
		            + "</style><section class='card' style=\" height:100%; width:100%; margin:0; \">" \
		            + mustache.render(reqTemplate.afmt, self.__buildStubbleDict(reqNote)) + "</section>"
		
		questionTg = premailer.transform(questionTg)
		answerTag = premailer.transform(answerTag)
		
		return Card(cid, questionTg, answerTag)
	
	def __buildStubbleDict(self, note: Note):
		cflds = note.flds.split(u"")
		temp_dict = {}
		for f, v in zip(note.model.flds, cflds):
			temp_dict[str(f)] = str(v)
		temp_dict["Tags"] = [i for i in note.tags if i]
		return temp_dict
	
	def __buildCssForOrd(self, css, ordi):
		defaultCardCss = get_rule_for_selector(css, ".card")
		ordinalCss = get_rule_for_selector(css, ".card{}".format(ordi + 1))
		try:
			ordProp = [prop for prop in ordinalCss.style.getProperties()]
			for dprop in defaultCardCss.style.getProperties():
				if dprop.name in [n.name for n in ordProp]:
					defaultCardCss.style[dprop.name] = ordinalCss.style.getProperty(dprop.name).value
		except:
			pass
		if defaultCardCss is not None:
			return defaultCardCss.cssText
		else:
			return ""
	
	def __getTemplateofOrd(self, templates, ord: int):
		for templ in templates:
			if (templ.ord == ord):
				return templ
