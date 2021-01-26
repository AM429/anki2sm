import json
import os
import shutil
from pathlib import Path
from zipfile import ZipFile


def move_media_to_smmedia(f):
	if f not in os.listdir(str(os.path.expandvars(r'%LocalAppData%') + "\\temp\\smmedia\\")):
		try:
			shutil.move(os.getcwd() + "\\out\\out_files\\elements\\" + f,
			            str(os.path.expandvars(r'%LocalAppData%') + "\\temp\\smmedia\\"))
		except:
			pass


def moveExtractedFiles(elements, k, media, p):
	shutil.move(p.joinpath(k).as_posix(), elements.joinpath(media[k]).as_posix())


def unpack_media(media_dir: Path):
	# if not media_dir.exists():
	#	raise FileNotFoundError
	
	with open(media_dir.joinpath("media").as_posix(), "r") as f:
		m = json.loads(f.read())
		print(f'\tAmount of media files: {len(m)}\n')
	return m


def unzip_file(zipfile_path: Path) -> Path:
	"""Attempts at unzipping the file, if the apkg is corrupt or is not appear to be zip, raises an Exception"""
	# if "zip" not in magic.from_file(zipfile_path.as_posix(), mime=True):
	# 	raise Exception("Error: apkg does not appear to be a ZIP file...")
	with ZipFile(zipfile_path.as_posix(), 'r') as apkg:
		apkg.extractall(zipfile_path.stem)
	return Path(zipfile_path.stem)