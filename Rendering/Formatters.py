import re
from gettext import gettext
from html.entities import name2codepoint

import mustache

reComment = re.compile("(?s)<!--.*?-->")
reStyle = re.compile("(?si)<style.*?>.*?</style>")
reScript = re.compile("(?si)<script.*?>.*?</script>")
reTag = re.compile("(?s)<.*?>")
reEnts = re.compile(r"&#?\w+;")
reMedia = re.compile("(?i)<img[^>]+src=[\"']?([^\"'>]+)[\"']?[^>]*>")
reSound = re.compile(r"\[sound:[^]]+\]")


def entsToTxt(html: str) -> str:
	# entitydefs defines nbsp as \xa0 instead of a standard space, so we
	# replace it first
	html = html.replace("&nbsp;", " ")
	
	def fixup(m):
		text = m.group(0)
		if text[:2] == "&#":
			# character reference
			try:
				if text[:3] == "&#x":
					return chr(int(text[3:-1], 16))
				else:
					return chr(int(text[2:-1]))
			except ValueError:
				pass
		else:
			# named entity
			try:
				text = chr(name2codepoint[text[1:-1]])
			except KeyError:
				pass
		return text  # leave as is
	
	return reEnts.sub(fixup, html)


def stripHTML(s: str) -> str:
	s = reComment.sub("", s)
	s = reStyle.sub("", s)
	s = reScript.sub("", s)
	s = reTag.sub("", s)
	s = entsToTxt(s)
	return s


def _removeFormattingFromMathjax(txt, ordi) -> str:
	creg = clozeReg.replace("(?si)", "")
	in_mathjax = False
	
	def replace(match):
		nonlocal in_mathjax
		if match.group("mathjax_open"):
			if in_mathjax:
				print("MathJax opening found while already in MathJax")
			in_mathjax = True
		elif match.group("mathjax_close"):
			if not in_mathjax:
				print("MathJax close found while not in MathJax")
			in_mathjax = False
		elif match.group("cloze"):
			if in_mathjax:
				return match.group(0).replace("{{c{}::".format(ordi), "{{C{}::".format(ordi))
		else:
			print("Unexpected: no expected capture group is present")
		return match.group(0)
	
	return re.sub(r"(?si)(?P<mathjax_open>\\[([])|(?P<mathjax_close>\\[\])])|(?P<cloze>" + (creg % ordi) + ")", replace,
	              txt)


FURIGANA = re.compile(r" ?([^ >]+?)\[(.+?)\]")

clozeReg = r"(?si)\{\{(?P<tag>c)%s::(?P<content>.*?)(::(?P<hint>.*?))?\}\}"

CLOZE_REGEX_MATCH_GROUP_TAG = "tag"
CLOZE_REGEX_MATCH_GROUP_CONTENT = "content"
CLOZE_REGEX_MATCH_GROUP_HINT = "hint"


def _clozeText(txt: str, ordi: str, type: str) -> str:
	"""Process the given Cloze deletion within the given template."""
	reg = clozeReg
	currentRegex = clozeReg % ordi
	if not re.search(currentRegex, txt):
		# No Cloze deletion was found in txt.
		return ""
	txt = _removeFormattingFromMathjax(txt, str(ordi))
	
	def repl(m):
		if type == "q":
			if m.group(CLOZE_REGEX_MATCH_GROUP_HINT):
				buf = "[%s]" % m.group(CLOZE_REGEX_MATCH_GROUP_HINT)
			else:
				buf = "[...]"
		else:
			buf = m.group(CLOZE_REGEX_MATCH_GROUP_CONTENT)
		# uppercase = no formatting
		if m.group(CLOZE_REGEX_MATCH_GROUP_TAG) == "c":
			buf = "<span class=cloze>%s</span>" % buf
		return buf
	
	if type == 'q':
		txt = re.sub(currentRegex, repl, txt)
		# and display other clozes normally
		return re.sub(reg % r"\d+", "\\2", txt)
	else:
		txt = re.search(currentRegex, txt)
		if txt:
			return repl(txt)


# filter args is a regex argument to the cloze {{c%s}}
def _cloze_filter(field_text: str, filter_args: str, q_or_a: str):
	return _clozeText(field_text, filter_args, q_or_a)


def cloze_q_filter(field_text: str, filter_args: str, *args):
	return _cloze_filter(field_text, filter_args, "q")


def cloze_a_filter(field_text: str, filter_args: str, *args):
	return _cloze_filter(field_text, filter_args, "a")


def text_filter(txt: str, *args) -> str:
	return stripHTML(txt)


def hint_filter(txt: str, args, context, tag: str, fullname) -> str:
	if not txt.strip():
		return ""
	domid = "hint%d" % id(txt)
	return """<a class=hint href="#"onclick="this.style.display='none';document.getElementById('%s').style.display='block';return false;">
    %s</a><div id="%s" class=hint style="display: none">%s</div>
    """ % (
		domid,
		gettext("Show %s") % tag,
		domid, txt,
	)


def captured_sound(groups: re.Match):
	return groups.group(2).startswith("sound")


def kana_filter(txt: str) -> str:
	def replace(match: re.Match) -> str:
		if captured_sound(match):
			return match.group(0)
		else:
			return match.group(2)
	
	return FURIGANA.sub(replace, txt.replace("&nbsp;", " "))


def kanji_filter(txt: str) -> str:
	def replace(match: re.Match) -> str:
		if captured_sound(match):
			return match.group(0)
		else:
			return match.group(1)
	
	return FURIGANA.sub(replace, txt.replace("&nbsp;", " "))


def furigana_filter(txt: str) -> str:
	def replace(match: re.Match) -> str:
		if captured_sound(match):
			return match.group(0)
		else:
			return "<ruby><rb>{}</rb><rt>{}</rt></ruby>"\
                                    .format(match.group(1),
                                            match.group(2))
	return FURIGANA.sub(replace, txt.replace("&nbsp;", " "))



# #EXPANDS THE CLOSES INTO Hint and the actual Text
# given expand_clozes("{{c1::a}} {{c2::b}} {{c3::c}} {{c4::d}}")
# output ['[...] b cd', 'a [...] cd', 'a b [...]d', 'a b c [...]', 'a b c d']
# first second third forth fifth .... continues in order
def expand_clozes(string: str):
	ords = set(re.findall(r"{{c(\d+)::.+?}}", string))
	strings = []
	
	def qrepl(m):
		if m.group(CLOZE_REGEX_MATCH_GROUP_HINT):
			return "[%s]" % m.group(CLOZE_REGEX_MATCH_GROUP_HINT)
		else:
			return "[...]"
	
	def arepl(m):
		return m.group(CLOZE_REGEX_MATCH_GROUP_CONTENT)
	
	for ord in ords:
		s = re.sub(clozeReg % ord, qrepl, string)
		s = re.sub(clozeReg % ".+?", arepl, s)
		strings.append(s)
	strings.append(re.sub(clozeReg % ".+?", arepl, string))
	return strings


mustache.filters["hint"] = hint_filter
mustache.filters["Text"] = text_filter

mustache.filters["furigana"] = furigana_filter
mustache.filters["kanji"] = kanji_filter
mustache.filters["kana"] = kana_filter