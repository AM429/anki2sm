import os
import sys
import time
import json
import errno
import shutil
import sqlite3
import logging
import cssutils
import threading
import itertools
import Configuration
from os import listdir
from yattag import Doc
from magic import magic
from os.path import isfile, join
from Rendering import Formatters
from Configuration import SMMEDIA
from collections import defaultdict
from Utils.Fonts import install_font
from pathlib import Path, WindowsPath
from progress.bar import IncrementalBar
from datetime import datetime, timedelta
from Utils.ErrorHandling import ep, pp, wp
from Rendering.Renderer import CardRenderer
from Rendering.MediaConverter import __CONVERTER_PROCESS, Q1
from concurrent.futures.thread import ThreadPoolExecutor
from Utils.FileUtils import \
	(
	move_media_to_smmedia,
	moveExtractedFiles,
	check_if_unzipped,
	unpack_media,
	unzip_file,
)
from Utils.HtmlUtils import \
	(
	wrapHtmlIn,
	strip_control_characters,
	cleanHtml,
	insertHtmlAt
)
from Models import \
	(
	Model,
	Template,
	Card,
	Collection,
	SQLNote
)

sys.setrecursionlimit(200000000)
cssutils.log.setLevel(logging.CRITICAL)

SUB_DECK_MARKER = '<sub_decks>'

Anki_Collection_IDs = []
AnkiModels = {}
totalCardCount = 0

doc, tag, text = Doc().tagtext()

IMAGES_TEMP = ()
FAILED_DECKS = []
DATA_ACCESS = None
ALLOW_IE_COMPAT = True
config = Configuration.ConverterConfig()


# ============================================ Other Util Stuff But Deck related =================================


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
def resetGlobals() -> None:
	global AnkiModels, totalCardCount, doc, tag, text, IMAGES_TEMP
	ALLOW_IE_COMPAT = True
	AnkiModels = {}
	IMAGES_TEMP = ()
	totalCardCount = 0
	doc, tag, text = Doc().tagtext()


def unpack_db(path: Path) -> None:
	conn = sqlite3.connect(path.joinpath("collection.anki2").as_posix())
	cursor = conn.cursor()
	
	cursor.execute("SELECT models,decks FROM col")
	
	dt = DeckTree()
	
	for row in cursor.fetchall():
		models, decks = row
		dt.buildColTree(decks)
		buildModels(models)
	
	exp = Exporter(dt)
	exp.buildNCDRecursively(path)
	
	print("\tExporting into xml...\n\n")


# ============================================= Deck Builder Functions =============================================
class DeckTree(object):
	
	def __init__(self):
		self.Anki_Collections = defaultdict(dict, ((SUB_DECK_MARKER, []),))
		self.__subDecks = set([])
	
	def getCollection(self):
		return self.Anki_Collections
	
	def attach(self, key, branch, trunk) -> None:
		"""Insert a branch of Decks on its trunk."""
		parts = branch.split('::', 1)
		if len(parts) == 1:  # branch is a leaf sub-deck
			trunk[SUB_DECK_MARKER].append(Collection(key, parts[0]))
		else:
			node, others = parts
			if node not in trunk:
				trunk[node] = defaultdict(dict, ((SUB_DECK_MARKER, []),))
			self.__subDecks.add(node)
			self.attach(key, others, trunk[node])
	
	def prettyDeckTree(self, d, indent=0):
		for key, value in d.items():
			if key == SUB_DECK_MARKER:
				if value:
					print('  ' * indent + str(value))
			else:
				print('  ' * indent + str(key))
				if isinstance(value, dict):
					self.prettyDeckTree(value, indent + 1)
				else:
					print('  ' * (indent + 1) + str(value))
	
	def isSubDeck(self, name: str) -> bool:
		return name in self.__subDecks
	
	def getSubDeck(self, name: str) -> Collection:
		def helper(d: dict, in_name: str) -> Collection:
			res = None
			for key, value in d.items():
				if key == SUB_DECK_MARKER:
					if value:
						for col in value:
							if col.name == in_name:
								res = col
				else:
					if isinstance(value, dict):
						if res is None:
							res = helper(value, in_name)
			return res
		
		return helper(self.Anki_Collections, name)
	
	def buildColTree(self, m: str):
		y = json.loads(m)
		decks = []
		with IncrementalBar("\tBuilding Collection Tree", max=len(y.keys())) as bar:
			for k in y.keys():
				self.attach(k, y[k]["name"], self.Anki_Collections)
				bar.next()
			bar.finish()


class Exporter(object):
	global doc, tag, text, AnkiModels
	
	def __init__(self, deckTree: DeckTree):
		self.dt = deckTree
	
	def buildNCDRecursively(self, path: Path):
		out = Path("out")
		out.mkdir(parents=True, exist_ok=True)
		
		def createCardsForDid(card_rdr, subdk):
			conn = sqlite3.connect(path.joinpath("collection.anki2").as_posix(), check_same_thread=False)
			cursor = conn.cursor()
			cursor.execute(f'SELECT id, nid, did, ord FROM cards WHERE did = {subdk.did}')
			rows = cursor.fetchall()
			print(f'Doing did = {subdk.did}')
			for row in rows:
				cid, nid, did, ordi = row
				
				SuperMemoElement(card_rdr.render_from_note(SQLNote(path, did, nid, AnkiModels), cid, ordi))
		
		def helper(a):
			for key, value in a.items():
				if key == SUB_DECK_MARKER:
					if value:
						for col in value:
							# CachedNotes[col.did]: DeckPagePool = buildNotesForDID(path, col.did)
							if not self.dt.isSubDeck(col.name):
								# SuperMemoTopic(col, col.name, createCardsForDid,CardRenderer(CachedNotes[col.did]))
								SuperMemoTopic(col, col.name, createCardsForDid, CardRenderer(None))
				else:
					if isinstance(value, dict):
						with tag("SuperMemoElement"):
							with tag('ID'):
								text(get_id())
							with tag('Title'):
								text(str(key))
							with tag('Type'):
								text('Topic')
							helper(value)
							subdk: Collection = self.dt.getSubDeck(key)
							# card_rdr = CardRenderer(CachedNotes[subdk.did])
							card_rdr = CardRenderer(None)
							if subdk is not None:
								createCardsForDid(card_rdr, subdk)
					else:
						if isinstance(value, Collection):
							print("THREE: ", value)
		
		with tag('SuperMemoCollection'):
			with tag('Count'):
				text(str(0))
			helper(self.dt.getCollection())
		
		with open(f"{out.as_posix()}/{str(os.path.split(path)[-1].split('.')[0])}.xml", "w", encoding="utf-8") as f:
			f.write(doc.getvalue())


def buildModels(t: str):
	global AnkiModels
	y = json.loads(t)
	templates = []
	flds = []
	with IncrementalBar("\tBuilding Models", max=len(y.keys())) as bar:
		for k in y.keys():
			AnkiModels[str(y[k]["id"])] = Model(str(
				y[k]["id"]),
				y[k]["type"],
				y[k]["css"],
				y[k]["latexPre"],
				y[k]["latexPost"]
			)
			
			for fld in y[k]["flds"]:
				flds.append((fld["name"], fld["ord"]))
			flds.sort(key=lambda x: int(x[1]))
			
			AnkiModels[str(y[k]["id"])].flds = tuple([f[0] for f in flds])
			
			for tmpl in y[k]["tmpls"]:
				templates.append(
					Template(tmpl["name"], tmpl["qfmt"],
					         tmpl["did"], tmpl["bafmt"],
					         tmpl["afmt"], tmpl["ord"],
					         tmpl["bqfmt"]
					         )
				)
			
			AnkiModels[str(y[k]["id"])].tmpls = tuple(templates)
			templates = []
			flds = []
			bar.next()
		bar.finish()


def start_import(file: str) -> int:
	filep = Path(file)
	if check_if_unzipped(Path(filep.stem)):
		p = Path(filep.stem)
	else:
		p = unzip_file(filep)
	
	if p is not None and type(p) is WindowsPath:
		media = unpack_media(p)
		print(f'\tAmount of media files: {len(media)}\n')
		
		out = Path("out")
		out.mkdir(parents=True, exist_ok=True)
		elements = Path(f"{out.as_posix()}/out_files/elements")
		
		try:
			os.makedirs(elements.as_posix())
		except:
			pass
		
		with ThreadPoolExecutor() as executor:
			futures = []
			for k in media:
				futures.append(
					executor.submit(
						moveExtractedFiles,
						elements=elements,
						k=k, media=media,
						p=p
					)
				)
		
		unpack_db(p)
		return 0
	else:
		ep("Error: Cannot convert %s" % os.path.basename(file))
		return -1


# =============================================SuperMemo Xml Output Functions =============================================

def cardHasData(card: Card) -> bool:
	if card != None:
		return card.ufactor and card.afactor and \
		       card.interval and card.lapses and \
		       card.last_rep and card.repetitions
	else:
		return False


def SuperMemoElement(card: Card) -> None:
	global doc, tag, text, get_id, IMAGES_TEMP,config
	IMAGES_TEMP = ()
	
	QContent_Sounds = ()
	QContent_Videos = ()
	
	AContent_Sounds = ()
	AContent_Videos = ()
	
	if "[sound:" in str(card.q):
		g = Formatters.reSound2.search(str(card.q))
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
		g = Formatters.reSound2.search(str(card.a))
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
				res = cleanHtml(a, imgcmp=config.images_as_component)
				
				if config.images_as_component:
					IMAGES_TEMP = IMAGES_TEMP + res["imgs"]
				
				a = insertHtmlAt(res["soup"], enforceSectionJS, 'head', 0)
				
				if ALLOW_IE_COMPAT:
					a = insertHtmlAt(a, liftIERestriction, 'head', 0)
				
				if not config.images_as_component and len(IMAGES_TEMP) != 0:
					a = insertHtmlAt(a, forcedCss, 'head', 0)
				
				a = strip_control_characters(a) \
					.encode("ascii", "xmlcharrefreplace") \
					.decode("utf-8")
				text(a)
			
			for s in QContent_Videos:
				with tag('Video'):
					with tag('URL'):
						text(SMMEDIA.format(s))
					with tag('Name'):
						text(s)
					if config.default_side != Configuration.SIDES[2] and \
							config.default_side != Configuration.SIDES[0]:
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
						text(SMMEDIA.format(s))
					with tag('Name'):
						text(s)
					with tag('Text'):
						text("")
					if config.default_side != Configuration.SIDES[2] and \
							config.default_side != Configuration.SIDES[0]:
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
				res = cleanHtml(card.a, imgcmp=config.images_as_component)
				if config.images_as_component:
					IMAGES_TEMP = IMAGES_TEMP + res["imgs"]
				a = insertHtmlAt(res["soup"], enforceSectionJS, 'head', 0)
				if ALLOW_IE_COMPAT:
					a = insertHtmlAt(a, liftIERestriction, 'head', 0)
				if not config.images_as_component and len(IMAGES_TEMP) != 0:
					a = insertHtmlAt(a, forcedCss, 'head', 0)
				a = strip_control_characters(a)
				a = a.encode("ascii", "xmlcharrefreplace").decode("utf-8")
				text(a)
			
			for s in AContent_Videos:
				with tag('Video'):
					with tag('URL'):
						text(os.path.expandvars(SMMEDIA.format(s)))
					with tag('Name'):
						text(s)
					if config.default_side != Configuration.SIDES[2] and \
							config.default_side != Configuration.SIDES[1]:
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
						text(os.path.expandvars(SMMEDIA.format(s)))
					with tag('Name'):
						text(s)
					with tag('Text'):
						text("")
					if config.default_side != Configuration.SIDES[2] and \
							config.default_side != Configuration.SIDES[1]:
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
						text(os.path.expandvars(SMMEDIA.format(img)))
					with tag('Name'):
						text(img)
					if config.default_side == Configuration.SIDES[1]:
						with tag("Question"):
							text("F")
						with tag("Answer"):
							text("T")
					elif config.default_side == Configuration.SIDES[0]:
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


def SuperMemoTopic(col, ttl, func, args) -> None:
	global doc, tag, text, get_id
	with tag("SuperMemoElement"):
		with tag('ID'):
			text(get_id())
		with tag('Title'):
			text(str(ttl))
		with tag('Type'):
			text('Topic')
		func(args, col)


# ============================================= Main Function =============================================

def main():
	global totalCardCount, config
	
	mypath = str(os.getcwd() + "\\apkgs\\")
	apkgfiles = [f for f in listdir(mypath) if isfile(join(mypath, f)) and f.endswith(".apkg")]
	
	if len(apkgfiles) == 0:
		ep("Error: No apkg in apkgs folder.")
		exit(0)
	
	
	if os.path.isfile('./anki2smConfig.cfg'):
		if 0 > config.loadConfig():
			config.prompt_for_config()
	else:
		config.prompt_for_config()
	
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
		
		start_time = time.time()
		
		start_import(mypath + apkgfiles[i])
		
		elapsed_time_secs = time.time() - start_time
		print(f'Conversion of Deck<{apkgfiles[i]}>: {str(timedelta(seconds=round(elapsed_time_secs)))}secs')
		
		resetGlobals()
		try:
			shutil.rmtree(os.path.splitext(apkgfiles[i])[0])
		except OSError as e:
			ep("Error: %s - %s." % (e.filename, e.strerror))
	
	# creating smmedia if it doesnot exist
	if not os.path.exists(SMMEDIA):
		try:
			os.makedirs(SMMEDIA)
		except OSError as e:
			if e.errno != errno.EEXIST:
				raise
	
	# moving media files to smmedia
	files = os.listdir(os.getcwd() + "\\out\\out_files\\elements")
	fonts = [x for x in files if x.endswith(".ttf")]
	failed_fonts = []
	for font in fonts:
		font_path = os.getcwd() + "\\out\\out_files\\elements\\" + font
		try:
			install_font(font_path.replace("\\", "/"))
		except:
			failed_fonts.append((font, font_path))
	
	if len(failed_fonts) > 0:
		ep("Error: Failed to install the fonts:\n")
	
	for ff in failed_fonts:
		f, fp = ff
		print(f'\t{f} [{fp}]')
	
	ep("\tRe-run script in admin mode if it is not or manually install the font.")
	
	if __CONVERTER_PROCESS is not None:
		Q1.put(("EXIT", "EXIT"))
	
	print("\nMoving Media Files DON'T CLOSE!")
	with ThreadPoolExecutor() as executor:
		futures = []
		for f in files:
			futures.append(executor.submit(move_media_to_smmedia, f=f))
	# deleting temp media files
	try:
		shutil.rmtree(os.getcwd() + "\\out\\out_files\\elements")
		shutil.rmtree(os.getcwd() + "\\out\\out_files")
	except OSError as e:
		ep("Error: %s - %s." % (e.filename, e.strerror))


if __name__ == '__main__':
	threading.stack_size(200000000)
	thread = threading.Thread(target=main)
	if not __CONVERTER_PROCESS.is_alive():
		__CONVERTER_PROCESS.start()
	thread.start()
	
	if len(FAILED_DECKS) > 0:
		wp("An Error occurred while processing the following decks:")
		for i in FAILED_DECKS:
			print(i)
		wp(
			"Please send an email to anki2sm.dev@protonmail.com with the attached deck(s) and the failed deck ids above.")
