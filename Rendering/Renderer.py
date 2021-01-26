import cssutils
from typing import Dict, Union

from Caching.CacheWorker import DeckPagePool
from Rendering import Formatters, mustache
from Models import Card, Note
import premailer

from Utils.HtmlUtils import get_rule_for_selector


class CardRenderer(object):
	def __init__(self, anki_notes: Union[Dict[str, Note], DeckPagePool]):
		self._AnkiNotes = anki_notes
		self.css_F = {}
		
	def mock(self, cid ,note_id,ordi:str):
		reqNote = self._AnkiNotes[note_id]
		if reqNote is None:
			print("BRUH")
			
	def render(self, cid ,note_id,ordi:str):
		reqNote = self._AnkiNotes[note_id]
		if reqNote.model.type == 0:
			return self._renderToNormalCard(cid, ordi,reqNote)
		elif reqNote.model.type == 1:
			return self._renderToClozeCard(cid, ordi, reqNote)
		
	def _renderToClozeCard(self, cid, ordi: str, reqNote: Note) -> Card:
		reqTemplate = self._getTemplateofOrd(reqNote.model.tmpls, 0)
		mustache.filters["cloze"] = lambda txt: Formatters.cloze_q_filter(txt, str(int(ordi) + 1))
		
		if reqNote.model.id+str(ordi) in self.css_F.keys():
			css = self.css_F[reqNote.model.id+str(ordi)]
		else:
			css = cssutils.parseString(reqNote.model.css)
			css = self._buildCssForOrd(css, ordi) if css else ""
			self.css_F[reqNote.model.id+str(ordi)] = css
		
	
		questionTg = "<style> " + css + " </style><section class='card' style=\" height:100%; width:100%; margin:0; \">" \
		             + mustache.render(reqTemplate.qfmt, self._buildStubbleDict(reqNote)) + "</section>"
		mustache.filters["cloze"] = lambda txt: Formatters.cloze_a_filter(txt, str(int(ordi) + 1))
		
		answerTag = "<section class='card' style=\" height:100%; width:100%; margin:0; \">" \
		            + mustache.render(reqTemplate.afmt, self._buildStubbleDict(reqNote)) + "</section>"
		questionTg = premailer.transform(questionTg)
		answerTag = premailer.transform(answerTag)
		
		return Card(cid, questionTg, answerTag)
	
	def _renderToNormalCard(self, cid, ordi: str, reqNote: Note) -> Card:
		reqTemplate = self._getTemplateofOrd(reqNote.model.tmpls, int(ordi))
		
		if reqNote.model.id + str(ordi) in self.css_F.keys():
			css = self.css_F[reqNote.model.id + str(ordi)]
		else:
			css = cssutils.parseString(reqNote.model.css)
			css = self._buildCssForOrd(css, ordi) if css else ""
			self.css_F[reqNote.model.id + str(ordi)] = css

		
		questionTg = "<style> " + css \
		             + "</style><section class='card' style=\" height:100%; width:100%; margin:0; \">" \
		             + mustache.render(reqTemplate.qfmt, self._buildStubbleDict(reqNote)) + "</section>"
		answerTag = "<style> " + css \
		            + "</style><section class='card' style=\" height:100%; width:100%; margin:0; \">" \
		            + mustache.render(reqTemplate.afmt, self._buildStubbleDict(reqNote)) + "</section>"
		
		questionTg = premailer.transform(questionTg)
		answerTag = premailer.transform(answerTag)
		
		return Card(cid, questionTg, answerTag)
	
	def _buildStubbleDict(self, note: Note):
		cflds = note.flds.split(u"")
		temp_dict = {}
		for f, v in zip(note.model.flds, cflds):
			temp_dict[str(f)] = str(v)
		temp_dict["Tags"] = [i for i in note.tags if i]
		return temp_dict
	
	def _buildCssForOrd(self, css, ordi):
		pagecss = css
		defaultCardCss = get_rule_for_selector(pagecss, ".card")
		ordinalCss = get_rule_for_selector(pagecss, ".card{}".format(ordi + 1))
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
	
	def _getTemplateofOrd(self, templates, ord: int):
		for templ in templates:
			if (templ.ord == ord):
				return templ
