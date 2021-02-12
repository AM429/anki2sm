# ============================================= Configuration =============================================
import os
from config import Config
from Utils.ErrorHandling import ep

SIDES = ("q", "a", "anki")
SMMEDIA = os.path.expandvars(r'%LocalAppData%') + "\\temp\\smmedia\\{}"


class ConverterConfig(object):
	def __init__(self):
		self.images_as_component = None
		self.default_side = SIDES[2]
		self.import_learning_data = None
	
	def loadConfig(self):
		f = open('anki2smConfig.cfg')
		cfg = Config(f)
		try:
			tempIMAGES_AS_COMPONENT = cfg.get("img_as_component", False)
			tempDEFAULT_SIDE = cfg["default_side"] if cfg["default_side"] in SIDES else "anki"
			tempIMPORT_LEARNING_DATA = cfg.get("import_learning_data", False)
			
			self.images_as_component = tempIMAGES_AS_COMPONENT
			self.default_side = tempDEFAULT_SIDE
			self.import_learning_data = tempIMPORT_LEARNING_DATA
		except:
			ep("Error: Corrupt Configuration file!")
			return -1
		finally:
			f.close()
		return 0
	
	def saveConfig(self):
		with open('anki2smConfig.cfg', 'w+') as f:
			f.write(f'{"img_as_component"}:{self.images_as_component}\n')
			f.write(f'{"default_side"}:\"{self.default_side}\"\n')
			f.write(f'{"import_learning_data"}:{self.import_learning_data}\n')
	
	def prompt_for_config(self):
		# Asking the user how they want the images to be displayed
		print("Do You want images as:")
		print("\tY - A separate component ")
		print("\tN - Embedded within the Html - experimental")
		tempInp: str = str(input(""))
		if tempInp.casefold() in "Y".casefold():
			self.images_as_component = True
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
			self.default_side = SIDES[tempInp - 1]
		# Asking the user if they want to save the options as a configuration file
		print("Do you want to save options for later? (Y/N)")
		tempInp: str = str(input(""))
		if tempInp.casefold() in "Y".casefold():
			self.saveConfig()
