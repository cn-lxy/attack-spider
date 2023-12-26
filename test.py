from translate import Translator

translator = Translator()

src = '''
secretsdump.py
'''

dst = translator.translate(src, dest='zh-CN').text

print(dst)
