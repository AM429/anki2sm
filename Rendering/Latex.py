import binascii
import re
from pdf2image import convert_from_bytes
import subprocess
from typing import AnyStr, Tuple
from Cryptodome.Hash import SHA1

from Formatters import stripHTML

LATEX = re.compile(r"(?xsi)\[latex\](.+?)\[/latex\]|\[\$\](.+?)\[/\$\]|\[\$\$\](.+?)\[/\$\$\]")
LATEX_NEWLINES = re.compile(r"(?xi)<br(/)?>|<div>")


class ExtractedLatex(object):
	def __init__(self, fname: str, latex: str):
		self.fname = fname
		self.latex = latex
	
	def __str__(self):
		return "ExtractedLatex {\n\tfname:" + self.fname + ", \n\tlatex:" + self.latex + "\n}"
	
	def __repr__(self):
		return "ExtractedLatex {\n\tfname:" + self.fname + ", \n\tlatex:" + self.latex + "\n}"


def _string_checksum(string: AnyStr) -> bytes:
	h = SHA1.new()
	h.update(string.encode())
	return h.hexdigest()[:20].encode()


def contains_latex(text: AnyStr) -> bool:
	return LATEX.match(text) is not None


def fname_for_latex(latex: str, is_svg: bool) -> str:
	ext = "svg" if is_svg else "png"
	csum = binascii.hexlify(_string_checksum(latex)).decode()
	return "latex-{}.{}".format(csum, ext)


def image_link_for_fname(fname: str) -> str:
	return "<img class=latex src=\"{}\">".format(fname)


def strip_html_for_latex(html: str) -> str:
	out = html
	o = LATEX_NEWLINES.sub("\n", html)
	if o is not None:
		out = o
	o = stripHTML(out)
	if o is not None:
		out = o
	return out


def export_latex(latex_src: ExtractedLatex, latexPre: str, latexPost: str) -> None:
	filename = latex_src.fname.split(".")[0] + '.tex'
	template = r'''\documentclass[preview]{{standalone}}\begin{{document}}{}\end{{document}}'''
	with open(filename, 'wb') as f:
		f.write(bytes(template.format(str(latex_src.latex.replace("\n", " \\\\ "))), 'UTF-8'))
	
	subprocess.call('pdflatex ' + filename, shell=True, )
	
	images = convert_from_bytes(open(latex_src.fname.split(".")[0] + ".pdf", 'rb').read())
	images[0].save(latex_src.fname.split(".")[0] + ".png")


def extract_latex(text: str, svg: bool) -> [AnyStr, [ExtractedLatex]]:
	extracted = []
	
	def replace(match: re.Match) -> str:
		latex = None
		m1, m2, m3 = match.group(1), match.group(2), match.group(3)
		if m1 is not None:
			latex = m1
		elif m2 is not None:
			latex = "${}$".format(m2)
		elif m3 is not None:
			latex = r"\begin{{displaymath}}{}\end{{displaymath}}".format(m3)
		
		latex_text = strip_html_for_latex(latex);
		
		fname = fname_for_latex(latex_text, svg);
		
		img_link = image_link_for_fname(fname);
		
		extracted.append(ExtractedLatex
			(
			fname,
			latex=latex_text
		)
		)
		return img_link
	
	return LATEX.sub(replace, text), extracted


if __name__ == '__main__':
	latexPre = "\\documentclass[12pt]{article}\n\\special{papersize=3in,5in}\n\\usepackage{amssymb,amsmath}\n\\pagestyle{empty}\n\\setlength{\\parindent}{0in}\n\\begin{document}\n"
	latexPost = "\\end{document}"
	export_latex(extract_latex("a[latex]one<br>and<div>two[/latex]b", False)[1][0], latexPre,
	             latexPost)  # , end="\n\n")
	export_latex(extract_latex("[$]<b>hello</b>&nbsp; world[/$]", True)[1][0], latexPre, latexPost)  # , end="\n\n")
	export_latex(extract_latex("[$$]math &amp; stuff[/$$]", False)[1][0], latexPre, latexPost)  # ,end="\n\n")
