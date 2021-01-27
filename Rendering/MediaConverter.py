from svglib.svglib import svg2rlg
from reportlab.graphics import renderPM
from PIL import Image
import os
import time
from multiprocessing import Process, Queue


def converter_process(in_queue:Queue):
	def convert_Svg(ext, filepath):
		file = filepath.replace(ext, "png")
		drawing = svg2rlg(filepath)
		renderPM.drawToFile(drawing, file, fmt="PNG")
		convert_png(filepath.replace(ext, "jpg"), file)
		os.remove(file)
	
	def convert_png(ext, filepath):
		file = filepath.replace(ext, "jpg")
		im = Image.open(filepath)
		rgb_im = im.convert('RGB')
		rgb_im.save(file)
	
	while True:
		data = in_queue.get()
		if data is not None:
			ext, filepath  = data
			try:
				if ext == "svg":
					convert_Svg(ext, filepath)
				elif ext == "png":
					convert_png(ext, filepath)
				elif ext == "EXIT" and filepath == "EXIT":
					if in_queue.empty():
						exit(0)
					else:
						in_queue.put(("EXIT","EXIT"))
			except IOError:
				in_queue.put((ext, filepath))
		else:
			time.sleep(0.5)


Q1 = Queue()
__CONVERTER_PROCESS = Process(target=converter_process, args=(Q1,))

class MediaConverter:
	# anki jpg png gif  tiff svg tif jpeg mp3 ogg wav avi ogv
	# sm   jpg png gif              jpeg mp3         avi mp4  bmp
	def __init__(self):
		self._alreadyConverted = {}
	
	def convertImage(self, filepath: str) -> str:
		global Q1
		if "\\" in filepath:
			filepath = filepath.replace("\\", "/")
		ext = filepath.split("/")[-1].split(".")[-1]
		filename = filepath.split("/")[-1]
		
		if filename in self._alreadyConverted.keys():
			return self._alreadyConverted[filename]
		
		filepath = filepath.replace(ext, ext.lower())
		file = filepath
		ext = ext.lower()
		if ext not in ["jpg"]:
			Q1.put((ext, filepath))
			file = filepath.replace(ext, "jpg")
		self._alreadyConverted[filename] = file
		
		return file
