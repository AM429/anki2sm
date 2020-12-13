import errno
import os
import re
import shutil
import sqlite3
from datetime import datetime
from os import listdir
from os.path import isfile, join
from pathlib import Path, WindowsPath
import json
from collections import defaultdict
from zipfile import ZipFile
from progress.bar import IncrementalBar
from magic import magic
import Formatters
import mustache
from yattag import Doc
import itertools
import premailer
import cssutils
import logging
import click
from Utils.Fonts import install_font
from config import Config
from Utils.HtmlUtils import \
	(
	wrapHtmlIn,
	strip_control_characters,
	cleanHtml,
	get_rule_for_selector,
	insertHtmlAt
)
from Models import \
	(
	Model,
	Template,
	Card,
	Collection,
	Note,
	EmptyString
)

cssutils.log.setLevel(logging.CRITICAL)

SUB_DECK_MARKER = '<sub_decks>'

Anki_Collections = defaultdict(dict, ((SUB_DECK_MARKER, []),))
AnkiNotes = {}
AnkiModels = {}
totalCardCount = 0

doc, tag, text = Doc().tagtext()

IMPORT_LEARNING_DATA = False
IMAGES_AS_COMPONENT = False
ALLOW_IE_COMPAT = True

SIDES = ("q", "a", "anki")

DEFAULT_SIDE = SIDES[2]

IMAGES_TEMP = ()
FAILED_DECKS = []


# ============================================ Other Util Stuff But Deck related =================================

def getDeckFromID(d, did: str):
	res = None
	for key, value in d.items():
		if key == SUB_DECK_MARKER:
			if value:
				for col in value:
					if col.did == did and res is None:
						res = col
		else:
			if isinstance(value, dict):
				if res is None:
					res = getDeckFromID(value, did)
			else:
				if isinstance(value, Collection):
					if value.did == did and res is None:
						res = value
	return res


def get_id_func():
	counter = itertools.count()
	next(counter)
	
	def p():
		return str(next(counter))
	
	return p


get_id = get_id_func()


#   Commented until a better understanding of anki is reached
#   	Code Source: https://groups.google.com/d/msg/supermemo_users/dTzhEog6zPk/8wqBk4qcCgAJ
#       Its Author: Mnd Mau
# def convert_time(x):
# 	if x == '':
# 		return ('')
# 	space = x.find(' ')
# 	if space == -1 and 'm' in x:
# 		return (1)
# 	if '(new)' in x:
# 		return (0)
# 	number = float(x[:space])
# 	if 'months' in x:
# 		return (round(number * 30))
# 	elif 'years' in x:
# 		return (round(number * 365))
# 	elif 'day' in x:
# 		return (round(number))
#
#
# def scale_afactor(a, min_ease, max_ease):
# 	return (6.868 - 1.3) * ((a - min_ease) / (max_ease - min_ease)) + 1.3

# ============================================= Some Util Functions =============================================

# Error Print
def ep(p) -> None:
	"""error print"""
	click.secho(str(">> " + p), fg="red", nl=False)


def pp(p) -> None:
	"""pretty print"""
	click.secho(">> ", fg="green", nl=False)
	click.echo(p)


def wp(p) -> None:
	"""warning print - yellow in color"""
	click.secho(p, fg="yellow", nl=True)


def resetGlobals() -> None:
	global Anki_Collections, AnkiNotes, AnkiModels, totalCardCount, doc, tag, text, IMAGES_TEMP, ALLOW_IE_COMPAT
	ALLOW_IE_COMPAT = True
	Anki_Collections = defaultdict(dict, ((SUB_DECK_MARKER, []),))
	AnkiNotes = {}
	AnkiModels = {}
	IMAGES_TEMP = ()
	totalCardCount = 0
	doc, tag, text = Doc().tagtext()


def unpack_db(path: Path) -> None:
	conn = sqlite3.connect(path.joinpath("collection.anki2").as_posix())
	cursor = conn.cursor()
	
	cursor.execute("SELECT * FROM col")
	for row in cursor.fetchall():
		did, crt, mod, scm, ver, dty, usn, ls, conf, models, decks, dconf, tags = row
		buildColTree(decks)
		buildModels(models)
		buildNotes(path)
		buildCardForNote(list(AnkiNotes.keys())[0], list(AnkiNotes.items())[0], 0, path)
	# buildCardsAndDeck(path)
	print("\tExporting into xml...\n\n")
	export(path)


def unpack_media(media_dir: Path):
	# if not media_dir.exists():
	#	raise FileNotFoundError
	
	with open(media_dir.joinpath("media").as_posix(), "r") as f:
		m = json.loads(f.read())
		print(f'\tAmount of media files: {len(m)}\n')
	return m


def unzip_file(zipfile_path: Path) -> Path:
	"""Attempts at unzipping the file, if the apkg is corrupt or is not appear to be zip, raises an Exception"""
	if "zip" not in magic.from_file(zipfile_path.as_posix(), mime=True):
		raise Exception("Error: apkg does not appear to be a ZIP file...")
	with ZipFile(zipfile_path.as_posix(), 'r') as apkg:
		apkg.extractall(zipfile_path.stem)
	return Path(zipfile_path.stem)


# ============================================= Deck Builder Functions =============================================

def attach(key, branch, trunk) -> None:
	"""Insert a branch of Decks on its trunk."""
	parts = branch.split('::', 1)
	if len(parts) == 1:  # branch is a leaf sub-deck
		trunk[SUB_DECK_MARKER].append(Collection(key, parts[0]))
	else:
		node, others = parts
		if node not in trunk:
			trunk[node] = defaultdict(dict, ((SUB_DECK_MARKER, []),))
		attach(key, others, trunk[node])


def prettyDeckTree(d, indent=0):
	for key, value in d.items():
		if key == SUB_DECK_MARKER:
			if value:
				print('  ' * indent + str(value))
		else:
			print('  ' * indent + str(key))
			if isinstance(value, dict):
				prettyDeckTree(value, indent + 1)
			else:
				print('  ' * (indent + 1) + str(value))


def isSubDeck(d: dict, name: str) -> bool:
	res = False
	for key, value in d.items():
		if key == name:
			res = True
		else:
			if isinstance(value, dict):
				if not res:
					res = isSubDeck(value, name)
	return res


def getSubDeck(d: dict, name: str) -> Collection:
	res = None
	for key, value in d.items():
		if key == SUB_DECK_MARKER:
			if value:
				for col in value:
					if col.name == name:
						res = col
		else:
			if isinstance(value, dict):
				if res is None:
					res = getSubDeck(value, name)
	return res


def buildColTree(m: str):
	global Anki_Collections
	y = json.loads(m)
	decks = []
	with IncrementalBar("\tBuilding Collection Tree", max=len(y.keys())) as bar:
		for k in y.keys():
			attach(k, y[k]["name"], Anki_Collections)
			bar.next()
		bar.finish()


def buildModels(t: str):
	global AnkiModels
	y = json.loads(t)
	templates = []
	flds = []
	with IncrementalBar("\tBuilding Models", max=len(y.keys())) as bar:
		for k in y.keys():
			AnkiModels[str(y[k]["id"])] = Model(str(y[k]["id"]), y[k]["type"], y[k]["css"], y[k]["latexPre"],
			                                    y[k]["latexPost"])
			
			for fld in y[k]["flds"]:
				flds.append((fld["name"], fld["ord"]))
			flds.sort(key=lambda x: int(x[1]))
			
			AnkiModels[str(y[k]["id"])].flds = tuple([f[0] for f in flds])
			
			for tmpl in y[k]["tmpls"]:
				templates.append(
					Template(tmpl["name"], tmpl["qfmt"],
					         tmpl["did"], tmpl["bafmt"],
					         tmpl["afmt"], tmpl["ord"],
					         tmpl["bqfmt"]))
			
			AnkiModels[str(y[k]["id"])].tmpls = tuple(templates)
			templates = []
			flds = []
			bar.next()
		bar.finish()


def buildNotes(path: Path):
	global AnkiNotes
	conn = sqlite3.connect(path.joinpath("collection.anki2").as_posix())
	cursor = conn.cursor()
	cursor.execute("SELECT * FROM notes")
	rows = cursor.fetchall()
	with IncrementalBar('\tBuilding Notes', max=len(rows)) as bar:
		for row in rows:
			nid, guid, mid, mod, usn, tags, flds, sfld, csum, flags, data = row
			reqModel = AnkiModels[str(mid)]
			AnkiNotes[str(nid)] = Note(reqModel, flds)
			AnkiNotes[str(nid)].tags = EmptyString(tags).split(" ")
			bar.next()
		bar.finish()


def buildCardForNote(note_id: int, note: Note, card_id: int, path: Path) -> [Card]:
	global AnkiModels, Anki_Collections, totalCardCount, FAILED_DECKS
	conn = sqlite3.connect(path.joinpath("collection.anki2").as_posix())
	cursor = conn.cursor()
	cursor.execute(f'SELECT * FROM cards WHERE nid = {str(note_id)}')
	rows = cursor.fetchall()
	for row in rows:
		genCard = None
	return None


def buildCardsAndDeck(path: Path):
	pass


# def buildCardsAndDeck(path: Path):
# 	global AnkiNotes, AnkiModels, Anki_Collections, totalCardCount, FAILED_DECKS
# 	conn = sqlite3.connect(path.joinpath("collection.anki2").as_posix())
# 	cursor = conn.cursor()
# 	cursor.execute(
# 		"SELECT * FROM cards ORDER BY factor ASC")  # min ease would at rows[0] and max index would be at rows[-1]
# 	rows = cursor.fetchall()
# 	with IncrementalBar("\tBuilding Cards and deck", max=len(rows)) as bar:
# 		for row in rows:
# 			cid, nid, did, ordi, mod, usn, crtype, queue, due, ivl, factor, reps, lapses, left, odue, odid, flags, data = row
# 			reqNote = AnkiNotes[str(nid)]
# 			genCard = None
#
# 			if reqNote.model.type == 0:
# 				reqTemplate = getTemplateofOrd(reqNote.model.tmpls, int(ordi))
#
# 				questionTg = "<style> " + buildCssForOrd(reqNote.model.css, ordi) \
# 				             + "</style><section class='card' style=\" height:100%; width:100%; margin:0; \">" \
# 				             + mustache.render(reqTemplate.qfmt, buildStubbleDict(reqNote)) + "</section>"
# 				answerTag = "<style> " + buildCssForOrd(reqNote.model.css, ordi) \
# 				            + "</style><section class='card' style=\" height:100%; width:100%; margin:0; \">" \
# 				            + mustache.render(reqTemplate.afmt, buildStubbleDict(reqNote)) + "</section>"
# 				questionTg = premailer.transform(questionTg)
# 				answerTag = premailer.transform(answerTag)
# 				genCard = Card(cid, questionTg, answerTag)
#
# 			elif reqNote.model.type == 1:
# 				reqTemplate = getTemplateofOrd(reqNote.model.tmpls, 0)
#
# 				mustache.filters["cloze"] = lambda txt: Formatters.cloze_q_filter(txt, str(int(ordi) + 1))
#
# 				css = reqNote.model.css
# 				css = buildCssForOrd(css, ordi) if css else ""
#
# 				questionTg = "<style> " + css + " </style><section class='card' style=\" height:100%; width:100%; margin:0; \">" \
# 				             + mustache.render(reqTemplate.qfmt, buildStubbleDict(reqNote)) + "</section>"
#
# 				mustache.filters["cloze"] = lambda txt: Formatters.cloze_a_filter(txt, str(int(ordi) + 1))
#
# 				answerTag = "<section class='card' style=\" height:100%; width:100%; margin:0; \">" \
# 				            + mustache.render(reqTemplate.afmt, buildStubbleDict(reqNote)) + "</section>"
#
# 				questionTg = premailer.transform(questionTg)
# 				answerTag = premailer.transform(answerTag)
# 				genCard = Card(cid, questionTg, answerTag)
#
# 			if genCard is not None:
# 				reqDeck = getDeckFromID(Anki_Collections, str(did))
# 				if reqDeck is not None:
# 					reqDeck.cards.append(genCard)
# 				else:
# 					if did not in FAILED_DECKS:
# 						FAILED_DECKS.append(did)
# 			else:
# 				if did not in FAILED_DECKS:
# 					FAILED_DECKS.append(did)
# 			totalCardCount += 1
# 			bar.next()
# 		bar.finish()


# ============================================= Import and Export Function =============================================

def export(file):
	global Anki_Collections
	out = Path("out")
	out.mkdir(parents=True, exist_ok=True)
	
	with tag('SuperMemoCollection'):
		with tag('Count'):
			text(str(totalCardCount))
		SuperMemoCollection(Anki_Collections)
	
	with open(f"{out.as_posix()}/" + os.path.split(file)[-1].split(".")[0] + ".xml", "w", encoding="utf-8") as f:
		f.write(doc.getvalue())


def start_import(file: str) -> int:
	p = unzip_file(Path(file))
	if p is not None and type(p) is WindowsPath:
		media = unpack_media(p)
		out = Path("out")
		out.mkdir(parents=True, exist_ok=True)
		elements = Path(f"{out.as_posix()}/out_files/elements")
		try:
			os.makedirs(elements.as_posix())
		except:
			pass
		for k in media:
			try:
				shutil.move(p.joinpath(k).as_posix(), elements.joinpath(media[k]).as_posix())
			except:
				pass
		unpack_db(p)
		return 0
	else:
		ep("Error: Cannot convert %s" % os.path.basename(file))
		return -1


# =============================================SuperMemo Xml Output Functions =============================================

def SuperMemoCollection(d: dict, indent=0):
	global doc, tag, text
	for key, value in d.items():
		if key == SUB_DECK_MARKER:
			if value:
				for col in value:
					if not isSubDeck(Anki_Collections, col.name):
						SuperMemoTopic(col, col.name)
		else:
			if isinstance(value, dict):
				with tag("SuperMemoElement"):
					with tag('ID'):
						text(get_id())
					with tag('Title'):
						text(str(key))
					with tag('Type'):
						text('Topic')
					SuperMemoCollection(value, indent=indent + 1)
					subdk = getSubDeck(Anki_Collections, key)
					if subdk:
						if subdk.cards is not None:
							for c in subdk.cards:
								SuperMemoElement(c)


def cardHasData(card: Card) -> bool:
	if card != None:
		return card.ufactor and card.afactor and \
		       card.interval and card.lapses and \
		       card.last_rep and card.repetitions
	else:
		return False


def SuperMemoElement(card: Card) -> None:
	global doc, tag, text, get_id, IMAGES_TEMP, DEFAULT_SIDE, SIDES
	IMAGES_TEMP = ()
	
	QContent_Sounds = ()
	QContent_Videos = ()
	
	AContent_Sounds = ()
	AContent_Videos = ()
	
	if "[sound:" in str(card.q):
		g = re.search(r"(?:\[sound:)([^])(?:]+)(?:\])", str(card.q))
		if g is not None:
			for p in g.groups():
				m = Path("{}/{}".format("out/out_files/elements", p))
				if m.exists():
					if any([ext in m.suffix for ext in ["mp3", "ogg", "wav"]]) \
							or "audio" in magic.from_file(m.as_posix(), mime=True):
						QContent_Sounds = QContent_Sounds + (p,)
					if any([ext in m.suffix for ext in ["mp4", "wmv", "mkv"]]) \
							or "video" in magic.from_file(m.as_posix(), mime=True):
						QContent_Videos = QContent_Videos + (p,)
	
	if "[sound:" in str(card.a):
		g = re.search(r"(?:\[sound:)([^])(?:]+)(?:\])", str(card.a))
		if g is not None:
			for p in g.groups():
				m = Path("{}/{}".format("out/out_files/elements", p))
				if m.exists():
					if any([ext in m.suffix for ext in ["mp3", "ogg", "wav"]]) \
							or "audio" in magic.from_file(m.as_posix(), mime=True):
						AContent_Sounds = AContent_Sounds + (p,)
					if any([ext in m.suffix for ext in ["mp4", "wmv", "mkv"]]) \
							or "video" in magic.from_file(m.as_posix(), mime=True):
						AContent_Videos = AContent_Videos + (p,)
	
	card.q = Formatters.reSound.sub("", card.q)
	card.a = Formatters.reSound.sub("", card.a)
	
	enforceSectionJS = """<script>document.createElement("section");</script>"""
	liftIERestriction = """<meta http-equiv="X-UA-Compatible" content="IE=10">"""
	forcedCss = """<style>img{max-width:50%;}</style>"""
	with tag('SuperMemoElement'):
		with tag('ID'):
			text(get_id())
		with tag('Type'):
			text('Item')
		with tag('Content'):
			with tag('Question'):
				a = wrapHtmlIn(card.q, 'head', 'body')
				res = cleanHtml(a, imgcmp=IMAGES_AS_COMPONENT)
				if IMAGES_AS_COMPONENT:
					IMAGES_TEMP = IMAGES_TEMP + res["imgs"]
				a = insertHtmlAt(res["soup"], enforceSectionJS, 'head', 0)
				if ALLOW_IE_COMPAT:
					a = insertHtmlAt(a, liftIERestriction, 'head', 0)
				if not IMAGES_AS_COMPONENT and len(IMAGES_TEMP) != 0:
					a = insertHtmlAt(a, forcedCss, 'head', 0)
				a = strip_control_characters(a)
				a = a.encode("ascii", "xmlcharrefreplace").decode("utf-8")
				text(a)
			
			for s in QContent_Videos:
				with tag('Video'):
					with tag('URL'):
						text(os.path.expandvars(r'%LocalAppData%') + "\\temp\\smmedia\\{}".format(s))
					with tag('Name'):
						text(s)
					if DEFAULT_SIDE != SIDES[2] and \
							DEFAULT_SIDE != SIDES[0]:
						with tag("Question"):
							text("F")
						with tag("Answer"):
							text("T")
					else:
						with tag("Question"):
							text("T")
						with tag("Answer"):
							text("F")
			
			for s in QContent_Sounds:
				with tag('Sound'):
					with tag('URL'):
						text(os.path.expandvars(r'%LocalAppData%') + "\\temp\\smmedia\\{}".format(s))
					with tag('Name'):
						text(s)
					with tag('Text'):
						text("")
					if DEFAULT_SIDE != SIDES[2] and \
							DEFAULT_SIDE != SIDES[0]:
						with tag("Question"):
							text("F")
						with tag("Answer"):
							text("T")
					else:
						with tag("Question"):
							text("T")
						with tag("Answer"):
							text("F")
			
			# html = Soup(a,'html.parser')
			# m=[p['href'] for p in html.find_all('a') ]
			# urls.append(m[0]) if len(m) else ""
			
			with tag('Answer'):
				res = cleanHtml(card.a, imgcmp=IMAGES_AS_COMPONENT)
				if IMAGES_AS_COMPONENT:
					IMAGES_TEMP = IMAGES_TEMP + res["imgs"]
				a = insertHtmlAt(res["soup"], enforceSectionJS, 'head', 0)
				if ALLOW_IE_COMPAT:
					a = insertHtmlAt(a, liftIERestriction, 'head', 0)
				if not IMAGES_AS_COMPONENT and len(IMAGES_TEMP) != 0:
					a = insertHtmlAt(a, forcedCss, 'head', 0)
				a = strip_control_characters(a)
				a = a.encode("ascii", "xmlcharrefreplace").decode("utf-8")
				text(a)
			
			for s in AContent_Videos:
				with tag('Video'):
					with tag('URL'):
						text(os.path.expandvars(r'%LocalAppData%') + "\\temp\\smmedia\\{}".format(s))
					with tag('Name'):
						text(s)
					if DEFAULT_SIDE != SIDES[2] and \
							DEFAULT_SIDE != SIDES[1]:
						with tag("Question"):
							text("T")
						with tag("Answer"):
							text("F")
					else:
						with tag("Question"):
							text("F")
						with tag("Answer"):
							text("T")
			
			for s in AContent_Sounds:
				with tag('Sound'):
					with tag('URL'):
						text(os.path.expandvars(r'%LocalAppData%') + "\\temp\\smmedia\\{}".format(s))
					with tag('Name'):
						text(s)
					with tag('Text'):
						text("")
					if DEFAULT_SIDE != SIDES[2] and \
							DEFAULT_SIDE != SIDES[1]:
						with tag("Question"):
							text("T")
						with tag("Answer"):
							text("F")
					else:
						with tag("Question"):
							text("F")
						with tag("Answer"):
							text("T")
			
			for img in IMAGES_TEMP:
				with tag('Image'):
					with tag('URL'):
						text(os.path.expandvars(r'%LocalAppData%') + "\\temp\\smmedia\\{}".format(img))
					with tag('Name'):
						text(img)
					if DEFAULT_SIDE == SIDES[1]:
						with tag("Question"):
							text("F")
						with tag("Answer"):
							text("T")
					elif DEFAULT_SIDE == SIDES[0]:
						with tag("Question"):
							text("T")
						with tag("Answer"):
							text("F")
			
			if False and cardHasData(card):
				with tag("LearningData"):
					with tag("Interval"):
						text("1")
					with tag("Repetitions"):
						text("1")
					with tag("Lapses"):
						text("0")
					with tag("LastRepetition"):
						text(datetime.date("").strftime("%d.%m.%Y"))
					with tag("AFactor"):
						text("3.92")
					with tag("UFactor"):
						text("3")


def SuperMemoTopic(col, ttl) -> None:
	global doc, tag, text, get_id
	with tag("SuperMemoElement"):
		with tag('ID'):
			text(get_id())
		with tag('Title'):
			text(str(ttl))
		# print(str(ttl))
		with tag('Type'):
			text('Topic')
		if col.cards != None:
			for c in col.cards:
				SuperMemoElement(c)


# ============================================= Configuration =============================================
def loadConfig():
	global IMAGES_AS_COMPONENT, DEFAULT_SIDE, IMPORT_LEARNING_DATA, SIDES
	f = open('anki2smConfig.cfg')
	cfg = Config(f)
	try:
		tempIMAGES_AS_COMPONENT = cfg.get("img_as_component", False)
		tempDEFAULT_SIDE = cfg["default_side"] if cfg["default_side"] in SIDES else "anki"
		tempIMPORT_LEARNING_DATA = cfg.get("import_learning_data", False)
		
		IMAGES_AS_COMPONENT = tempIMAGES_AS_COMPONENT
		DEFAULT_SIDE = tempDEFAULT_SIDE
		IMPORT_LEARNING_DATA = tempIMPORT_LEARNING_DATA
	except:
		ep("Error: Corrupt Configuration file!")
		return -1
	finally:
		f.close()
	return 0


def saveConfig():
	global IMAGES_AS_COMPONENT, DEFAULT_SIDE, IMPORT_LEARNING_DATA
	with open('anki2smConfig.cfg', 'w+') as f:
		f.write(f'{"img_as_component"}:{IMAGES_AS_COMPONENT}\n')
		f.write(f'{"default_side"}:\"{DEFAULT_SIDE}\"\n')
		f.write(f'{"import_learning_data"}:{IMPORT_LEARNING_DATA}\n')


def prompt_for_config():
	global IMAGES_AS_COMPONENT, DEFAULT_SIDE
	# Asking the user how they want the images to be displayed
	print("Do You want images as:")
	print("\tY - A separate component ")
	print("\tN - Embedded within the Html - experimental")
	tempInp: str = str(input(""))
	if tempInp.casefold() in "Y".casefold():
		IMAGES_AS_COMPONENT = True
	elif tempInp.casefold() != "N".casefold():
		print("Wrong input provided, proceeding as embedded")
	# Asking the user where they want the components to end up
	print("Where do you want the components to end up:")
	print("\t 1 = Front")
	print("\t 2 = Back ")
	print("\t 3 = Leave them as is")
	tempInp: int = int(input(""))
	if 0 >= tempInp > 3:
		print("Wrong input provided, proceeding as it is in anki")
	else:
		DEFAULT_SIDE = SIDES[tempInp - 1]
	# Asking the user if they want to save the options as a configuration file
	print("Do you want to save options for later? (Y/N)")
	tempInp: str = str(input(""))
	if tempInp.casefold() in "Y".casefold():
		saveConfig()


# ============================================= Main Function =============================================

def main():
	global AnkiNotes, totalCardCount, IMAGES_AS_COMPONENT, DEFAULT_SIDE, SIDES, ALLOW_IE_COMPAT
	
	mypath = str(os.getcwd() + "\\apkgs\\")
	apkgfiles = [f for f in listdir(mypath) if isfile(join(mypath, f))]
	
	if len(apkgfiles) == 0:
		ep("Error: No apkg in apkgs folder.")
		exit(0)
	
	if os.path.isfile('./anki2smConfig.cfg'):
		if 0 > loadConfig():
			prompt_for_config()
	else:
		prompt_for_config()
	
	for i in range(len(apkgfiles)):
		pp(f'Processing {apkgfiles[i]} : {i + 1}/{len(apkgfiles)}')
		
		print("Do you want to lift IE Restrictions: ")
		wp("Please be aware that selecting No is not going to allow you to embed images within the html.")
		print("\tY - Yes I want to left the restrictions.")
		print("\tN - No I choose to not lift the restrictions.")
		tempInp: str = str(input(""))
		if tempInp.casefold() in "N".casefold():
			ALLOW_IE_COMPAT = False
		elif tempInp.casefold() != "Y".casefold():
			print("Wrong input provided, IE restrictions are lifted")
		
		start_import(mypath + apkgfiles[i])
		resetGlobals()
		try:
			shutil.rmtree(os.path.splitext(apkgfiles[i])[0])
		except OSError as e:
			ep("Error: %s - %s." % (e.filename, e.strerror))
	
	# creating smmedia if it doesnot exist
	if not os.path.exists(str(os.path.expandvars(r'%LocalAppData%') + "\\temp\\smmedia\\")):
		try:
			os.makedirs(str(os.path.expandvars(r'%LocalAppData%') + "\\temp\\smmedia\\"))
		except OSError as e:
			if e.errno != errno.EEXIST:
				raise
	
	# moving media files to smmedia
	files = os.listdir(os.getcwd() + "\\out\\out_files\\elements")
	fonts = [x for x in files if x.endswith(".ttf")]
	for font in fonts:
		try:
			font_path = os.getcwd() + "\\out\\out_files\\elements\\" + font
			install_font(font_path.replace("\\", "/"))
		except:
			ep(
				"Error: Failed to install the font {}. \n\tRe-run script in admin mode if it is not or manually install it Path[{}].\n".format(
					font, font_path))
	
	with IncrementalBar("Moving Media Files DON'T CLOSE!", max=len(files)) as bar:
		for f in files:
			if f not in os.listdir(str(os.path.expandvars(r'%LocalAppData%') + "\\temp\\smmedia\\")):
				try:
					shutil.move(os.getcwd() + "\\out\\out_files\\elements\\" + f,
					            str(os.path.expandvars(r'%LocalAppData%') + "\\temp\\smmedia\\"))
				except:
					pass
			bar.next()
		bar.finish()
	
	# deleting temp media files
	try:
		shutil.rmtree(os.getcwd() + "\\out\\out_files\\elements")
		shutil.rmtree(os.getcwd() + "\\out\\out_files")
	except OSError as e:
		ep("Error: %s - %s." % (e.filename, e.strerror))


if __name__ == '__main__':
	main()
	if len(FAILED_DECKS) > 0:
		wp("An Error occured while processing the following decks:")
		for i in FAILED_DECKS:
			print(i)
		wp(
			"Please send an email to anki2sm.dev@protonmail.com with the attached deck(s) and the failed deck ids above.")
