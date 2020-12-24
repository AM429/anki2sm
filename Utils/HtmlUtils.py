import os
from xml.sax.saxutils import unescape
from bs4 import BeautifulSoup
from Rendering.Formatters import reSound
from Rendering.MediaConverter import MediaConverter

IMAGE_TO_ELEMENT_RATIO_W = 0.5
ELEMENT_TO_WINDOW_RATO = (0.5, 0.5)


def wrapHtmlIn(html: str, pointOfIns: str, tagtoWrapIn: str) -> str:
	tempSoup = BeautifulSoup(html, features="lxml")
	newBody = tempSoup.find(pointOfIns)
	bodytag = tempSoup.new_tag(tagtoWrapIn)
	for content in reversed(newBody.contents):
		bodytag.insert(0, content.extract())
	newBody.append(bodytag)
	return str(newBody)


def strip_control_characters(input):
	if input:
		import re
		
		# unicode invalid characters
		RE_XML_ILLEGAL = u'([\u0000-\u0008\u000b-\u000c\u000e-\u001f\ufffe-\uffff])' + \
		                 u'|' + \
		                 u'([%s-%s][^%s-%s])|([^%s-%s][%s-%s])|([%s-%s]$)|(^[%s-%s])' % \
		                 (chr(0xd800), chr(0xdbff), chr(0xdc00), chr(0xdfff),
		                  chr(0xd800), chr(0xdbff), chr(0xdc00), chr(0xdfff),
		                  chr(0xd800), chr(0xdbff), chr(0xdc00), chr(0xdfff),
		                  )
		input = re.sub(RE_XML_ILLEGAL, "", input)
		
		# ascii control characters
		input = re.sub(r"[\x01-\x1F\x7F]", "", input)
		# removing sound tags
		input = reSound.sub("", input, )
	
	return input


def cleanHtml(html, imgcmp=False):
	res = reallocateRes('img', html,
	                    "file:///" + os.path.expandvars(r'%LocalAppData%').replace("\\", "/") + "/temp/smmedia/",
	                    imgcomp=imgcmp)
	
	html = res["soup"]
	soup = BeautifulSoup(unescape(html), features="lxml")
	
	for script in soup(["script"]):
		if script == "script":
			script.extract()
	
	for tag in soup.findAll(True):
		for attr in [attr for attr in tag.attrs if
		             attr not in ["style", "name", "id", "class", "src", "href", "onclick"]]:
			del tag[attr]
	if (imgcmp):
		return {"soup": str(soup), "imgs": res["imgs"]}
	else:
		return {"soup": str(soup)}


def get_rule_for_selector(stylesheet, selector):
	for rule in stylesheet.cssRules:
		if hasattr(rule, "selectorList") and selector in [s.selectorText for s in rule.selectorList]:
			return rule


def insertHtmlAt(html, mod, target, pos):
	soup = BeautifulSoup(html, "html.parser")
	target = soup.find("head")
	toInsert = BeautifulSoup(mod, "html.parser")
	target.insert(pos, toInsert)
	return str(soup)


def reallocateRes(tag, text, location, imgcomp=False):
	imptple = ()
	soup = BeautifulSoup(unescape(text), features="lxml")
	for img in soup.find_all(tag):
		try:
			if img is not None:
				if 'src' in img.attrs.keys():
					if not imgcomp:
						img_urls = img['src']
						mc = MediaConverter()
						img_urls = mc.convertImage(os.getcwd() + "\\out\\out_files\\elements\\"+img_urls)
						img_urls = img_urls.split("/")[-1]
						# IMAGES_TEMP = IMAGES_TEMP + (img_urls,)
						img['src'] = location + img_urls
						print(location + img_urls)
					# img['width'] = "50%"
					# img["style"] = ""
					# img['src'] = "data:image/{};base64,{}".format(
					#	img_urls.split(".")[-1],
					#	encode_file_b64((location + img_urls).replace("file:///", "")).decode("utf-8"))
					else:
						img_urls = img['src']
						img.decompose()
						imptple = imptple + (img_urls,)
		except Exception as e:
			print("Failed at parsing this image", img, e)
	if imgcomp:
		return {"imgs": imptple, "soup": str(soup)}
	else:
		return {"soup": str(soup)}
