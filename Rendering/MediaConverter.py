from svglib.svglib import svg2rlg
from reportlab.graphics import renderPM
from PIL import Image
import os


class MediaConverter:
	# anki jpg png gif  tiff svg tif jpeg mp3 ogg wav avi ogv
	# sm   jpg png gif              jpeg mp3         avi mp4  bmp
	def convertImage(self, filepath: str) -> str:
		if "\\" in filepath:
			filepath = filepath.replace("\\", "/")
		ext = filepath.split("/")[-1].split(".")[-1]
		filepath = filepath.replace(ext,ext.lower())
		file = filepath
		ext = ext.lower()
		if ext not in ["jpg"]:
			if ext == "png":
				im = Image.open(filepath)
				rgb_im = im.convert('RGB')
				file = filepath.replace(ext, "jpg")
				rgb_im.save(file)
			if ext == "svg":
				drawing = svg2rlg(filepath)
				file = filepath.replace(ext, "png")
				renderPM.drawToFile(drawing, file, fmt="PNG")
				im = Image.open(file)
				
				rgb_im = im.convert('RGB')
				rgb_im.save(filepath.replace(ext, "jpg"))
				os.remove(file)
				file = filepath.replace(ext, "jpg")
		return file
