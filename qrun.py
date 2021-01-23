#qtext = """What is the key risk factor for Cervical Carcinoma?<div><br /></div><div>{{c1::High-risk HPV (16, 18, 31, 33)}}</div><div><i>HPV 16 and 18 account for more than 70% of all Cervical Carcinoma</i></div><div><i><br /></i></div><i><img src="paste-28157805593154.jpg" /></i>
#<img src="paste-344018290475011.jpg"><img src="paste-28630251995139.jpg"><img src="paste-341909461532675.jpg"><img src="paste-69376606732291.jpg"><img src="paste-66705137074179.jpg">
#<img src="paste-35699768164355.jpg"><i>Other:</i><div><div><i>-<b>&nbsp;smoking</b></i></div><div><i>- starting&nbsp;<b>sexual</b>&nbsp;intercourse at a&nbsp;<b>young</b>&nbsp;age</i></div><div><i>-<b>&nbsp;immunodeficiency</b>&nbsp;(eg.&nbsp;HIV infection)</i></div></div>"""
#q = qtext.split(r"")
#fonts.install_font("C:/Users/polit/AppData/Local/Temp/smmedia/_YUMIN.TTF")

#import glob
from Caching.CacheWorker import LRUIndex
from RangeDict import OrderedRangeDict

#print(glob.glob("C:\\Users\\polit\\AppData\\Local\\Temp\\smmedia\\*.ttf"))


rd = OrderedRangeDict({(1,6):"1 to 6",(10,12):"10 to 12",(69,99):"69 to 99"})


rd[(100,101)] ="kkk"
queu = LRUIndex(4)
queu.set((1,6),"1 to 6")
queu.set((10,12),"10 to 12")
queu.set((69,99),"69 to 99")

print(queu.get(11))
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