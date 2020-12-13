import cssutils
import mustache
import Formatters
from Models import Card, Note
import premailer

from Utils.HtmlUtils import get_rule_for_selector


class CardRenderer(object):
	def __init__(self,card: Card):
		self._card = card
	
	def render(self):
		pass
	
	def _renderToClozeCard(self,cid, ordi: str, reqNote) -> Card:
		reqTemplate = getTemplateofOrd(reqNote.model.tmpls, 0)
		mustache.filters["cloze"] = lambda txt: Formatters.cloze_q_filter(txt, str(int(ordi) + 1))
		
		css = reqNote.model.css
		css = self._buildCssForOrd(css, ordi) if css else ""
		
		questionTg = "<style> " + css + " </style><section class='card' style=\" height:100%; width:100%; margin:0; \">" \
		             + mustache.render(reqTemplate.qfmt, self._buildStubbleDict(reqNote)) + "</section>"
		mustache.filters["cloze"] = lambda txt: Formatters.cloze_a_filter(txt, str(int(ordi) + 1))
		answerTag = "<section class='card' style=\" height:100%; width:100%; margin:0; \">" \
		            + mustache.render(reqTemplate.afmt, self.buildStubbleDict(reqNote)) + "</section>"
		questionTg = premailer.transform(questionTg)
		answerTag = premailer.transform(answerTag)
		
		return Card(cid, questionTg, answerTag)
	
	def _renderToNormalCard(self,cid, ordi: str, reqNote: Note) -> Card:
		reqTemplate = getTemplateofOrd(reqNote.model.tmpls, int(ordi))
		
		questionTg = "<style> " + self._buildCssForOrd(reqNote.model.css, ordi) \
		             + "</style><section class='card' style=\" height:100%; width:100%; margin:0; \">" \
		             + mustache.render(reqTemplate.qfmt, self._buildStubbleDict(reqNote)) + "</section>"
		answerTag = "<style> " + self._buildCssForOrd(reqNote.model.css, ordi) \
		            + "</style><section class='card' style=\" height:100%; width:100%; margin:0; \">" \
		            + mustache.render(reqTemplate.afmt, self._buildStubbleDict(reqNote)) + "</section>"
		
		questionTg = premailer.transform(questionTg)
		answerTag = premailer.transform(answerTag)
		
		return Card(cid, questionTg, answerTag)
	
	def _buildStubbleDict(self,note: Note):
		cflds = note.flds.split(u"")
		temp_dict = {}
		for f, v in zip(note.model.flds, cflds):
			temp_dict[str(f)] = str(v)
		temp_dict["Tags"] = [i for i in note.tags if i]
		return temp_dict
	
	def _buildCssForOrd(self,css, ordi):
		pagecss = cssutils.parseString(css)
		defaultCardCss = get_rule_for_selector(pagecss, ".card")
		ordinalCss = get_rule_for_selector(pagecss, ".card{}".format(ordi + 1))
		try:
			ordProp = [prop for prop in ordinalCss.style.getProperties()]
			for dprop in defaultCardCss.style.getProperties():
				if (dprop.name in [n.name for n in ordProp]):
					defaultCardCss.style[dprop.name] = ordinalCss.style.getProperty(dprop.name).value
		except:
			pass
		if defaultCardCss is not None:
			return defaultCardCss.cssText
		else:
			return ""
