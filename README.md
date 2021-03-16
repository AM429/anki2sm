> taking a break for a while
# Anki to SuperMemo converter
  anki2sm is a python script that is meant to batch convert anki decks into supermemo decks, including audios, images and videos.   
  The scripts also comes with an additional feature of extracting annotated links, for incremental reading. It creates a bat file that when run opens explorer with multiple tabs. You can open supermemo to import these webpages.
  This script is meant to run on Windows. If you don't already use SuperMemo or are new to it, feel free to schedule call [here]( https://calendly.com/test0009/raj) with Raj to guide you through the basics of SuperMemo. You can find downloads of SuperMemo at [supermemo.wiki/learn](supermemo.wiki/learn]). 
  
### Steps for usage:
- clone this repo
- make sure requirements.txt is met or run the ```init.bat``` to install the dependancies
- create an ```apkgs``` folder and ```out``` folder within the root directory of the cloned repo
- paste your apkgs into the ```apkgs```
- run ```run.bat``` which should run the anki2smV2

For a guide on using anki2sm in video form, check out [this video](https://www.youtube.com/watch?v=j6dmQHMGTJs).

##### Some Notes:
  ##### Media:
   - Media from anki is stored into ```C:\Users\<your-username>\AppData\Local\Temp\smmedia```. You donot need to create the directory the script creates it. Tested with images and audio. 
  ##### Fonts:
   - Run the script in admin mode for it to install fonts that are sometimes bundled with apkgs.
# TODO: 
  1) [ ] Bug test it.
  2) [ ] Anki progress import.
  3) [x] Each collection should have its own concept or topic.
  4) [ ] Support Latex.
  5) [ ] Suport image occlusion. 
  6) [ ] Item names to reflect the content.


# Contributers:
 - [Raj](https://github.com/rajlego)
 
 - Leo

- [lotabout](https://github.com/lotabout/) ([Modified pymustache Library](https://github.com/lotabout/pymustache/blob/master/pymustache/mustache.py))

 ## Original Contributers 

- [KeepOnSurviving](https://github.com/KeepOnSurviving)

- [cutie](https://github.com/cutie)


