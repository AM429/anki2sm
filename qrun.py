from typing import List

import mustache
import Formatters
import Utils.Fonts as fonts

#qtext = """What is the key risk factor for Cervical Carcinoma?<div><br /></div><div>{{c1::High-risk HPV (16, 18, 31, 33)}}</div><div><i>HPV 16 and 18 account for more than 70% of all Cervical Carcinoma</i></div><div><i><br /></i></div><i><img src="paste-28157805593154.jpg" /></i>
#<img src="paste-344018290475011.jpg"><img src="paste-28630251995139.jpg"><img src="paste-341909461532675.jpg"><img src="paste-69376606732291.jpg"><img src="paste-66705137074179.jpg">
#<img src="paste-35699768164355.jpg"><i>Other:</i><div><div><i>-<b>&nbsp;smoking</b></i></div><div><i>- starting&nbsp;<b>sexual</b>&nbsp;intercourse at a&nbsp;<b>young</b>&nbsp;age</i></div><div><i>-<b>&nbsp;immunodeficiency</b>&nbsp;(eg.&nbsp;HIV infection)</i></div></div>"""
#q = qtext.split(r"")
#fonts.install_font("C:/Users/polit/AppData/Local/Temp/smmedia/_YUMIN.TTF")

#import glob
#print(glob.glob("C:\\Users\\polit\\AppData\\Local\\Temp\\smmedia\\*.ttf"))

# 
# mustache.filters["cloze"] = lambda txt: Formatters.cloze_q_filter(txt, str(int(0) + 1))
# 
# mytemplate = "{{#Text}}{{cloze:Text}}{{/Text}}"
# 
# print(mustache.render(mytemplate,{"Text": q[0]}))
# from MediaConverter import MediaConverter
#
# mc = MediaConverter()
# mc.convertImage("C:\\Users\\polit\\Desktop\\anki2sm\\out\\out_files\\elements\\Freesample.svg")


# def lastStoneWeightII( stones: List[int]) -> int:
# 	total = sum(stones)
#
# 	Max_weight = int(total / 2)
# 	print("Max Weight",Max_weight)
# 	current = (Max_weight + 1) * [0]
#
# 	for stone in stones:
# 		for wgt in range(Max_weight, -1, -1):
# 			if wgt - stone >= 0:
# 				current[wgt] = max(stone + current[wgt - stone], current[wgt])
# 			print(stone, wgt, current)
# 	#print("Matrix value:\n",current)
# 	return total - 2 * current[-1]
#
# lastStoneWeightII([2,7,4,1,8,1])
