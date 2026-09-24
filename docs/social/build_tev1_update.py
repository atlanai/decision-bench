"""Render evidence-backed Tev1 social cards; Pillow, no generated logos or figures."""
from pathlib import Path
import json
from PIL import Image, ImageDraw, ImageFont
R=Path(__file__).resolve().parents[2]; O=R/'docs/social'; E=R/'docs/benchmarks/tev1'
M=json.loads((E/'metrics.json').read_text()); C=json.loads((E/'paired-comparisons.json').read_text())
MODELS={m['id']:m for m in json.loads((R/'config/models.json').read_text())['models']}
for p in (R/'results/bench-v4').glob('*/metadata.json'):
 m=json.loads(p.read_text())['model'];MODELS.setdefault(m['id'],m)
BG='#fafaf8'; INK='#181b26'; MUTED='#5e6472'; ACC='#5340d5'; LINE='#dfdfe6'
F=Path('/System/Library/Fonts/Supplemental')
def font(n,bold=False):return ImageFont.truetype(str(F/('Arial Bold.ttf' if bold else 'Arial.ttf')),n)
def text(d,xy,s,n=32,fill=INK,bold=False):d.text(xy,s,font=font(n,bold),fill=fill)
def logo(im,x,y,size,name='together.ai'):
 p=R/f'site/assets/logos/{name}.png'
 if p.exists():
  v=Image.open(p).convert('RGBA');v.thumbnail((size,size));im.paste(v,(x+(size-v.width)//2,y+(size-v.height)//2),v)
def base(h):
 im=Image.new('RGB',(1800,h),BG);d=ImageDraw.Draw(im)
 text(d,(84,52),'DECISION BENCH',27,bold=True)
 text(d,(1370,52),'TEXT-ONLY EVALUATION',22,MUTED)
 return im,d
im,d=base(1125)
logo(im,84,146,125)
text(d,(240,150),'Tev1 4B Experimental',65,bold=True)
text(d,(243,229),'Together AI · Qwen3.5-4B fine-tune',32,MUTED)
d.line((84,314,1716,314),fill=LINE,width=2)
for x,value,label,detail in [(84,f'{M["accuracy"]:.1%}','ACCURACY',f'{M["correct"]} correct / {M["cases"]} text cases'),(650,f'{M["latency_ms"]["p50"]:.0f} ms','MEDIAN LATENCY','Serial, end-to-end API calls'),(1220,f'{M["cost_usd"]*100:.2f}¢','ESTIMATED RUN COST','Entire 949-case evaluation')]:
 text(d,(x,365),label,24,MUTED,True);text(d,(x,419),value,91,ACC,True);text(d,(x,534),detail,29,MUTED)
d.rounded_rectangle((84,635,1716,893),radius=22,fill='#eeecfa')
text(d,(120,667),'Same 949 cases',32,bold=True)
text(d,(120,730),'Tev1 4B',33,ACC,True);text(d,(380,730),'85.4%',47,ACC,True)
text(d,(680,730),'Jev 1.13',33,bold=True);text(d,(935,730),'93.2%',47,bold=True)
text(d,(1230,729),'7.8 points',42,bold=True);text(d,(1230,789),'accuracy gap',27,MUTED)
text(d,(120,832),'0 API or output-format errors in the full run',28,MUTED)
text(d,(84,942),'Tested: together/Tev1-4B-experimental · The 0.8B model was not tested.',27,MUTED)
text(d,(84,987),'122 image-containing cases excluded. Cost uses the announced token rate; not a billing receipt.',25,MUTED)
text(d,(84,1060),'decisionbench.ai',28,bold=True);text(d,(1310,1060),'bench-v4 · September 2026',23,MUTED)
im.save(O/'tev1-reply.png')

im,d=base(1390)
text(d,(84,123),'A new model on the same 949 cases',59,bold=True)
text(d,(84,205),'Tev1 4B joins a comparison across 13 models. Accuracy on one shared text-only subset.',30,MUTED)
rows=[{'model':x['model'],'accuracy':x['accuracy']} for x in C]+[{'model':'tev1-4b-experimental','accuracy':M['accuracy']}]
rows.sort(key=lambda x:-x['accuracy'])
text(d,(154,283),'MODEL',22,MUTED,True);text(d,(1070,283),'ACCURACY',22,MUTED,True);text(d,(1480,283),'CORRECT / 949',22,MUTED,True)
logos={'Google':'google.com','Anthropic':'anthropic.com','OpenAI':'openai.com','DeepSeek':'deepseek.com','Zhipu':'z.ai','Z.ai':'z.ai','Z.AI':'z.ai','Qwen':'qwen.ai','Alibaba':'alibabacloud.com','Amazon':'amazon.com','TypeSafe':'typesafe.ai','Together AI':'together.ai','Laya':'convaiinnovations.com','Convai':'convaiinnovations.com'}
for i,r in enumerate(rows):
 y=329+i*66;mid=r['model'];m=MODELS[mid];isnew=mid=='tev1-4b-experimental';color=ACC if isnew else '#767d8d'
 if isnew:d.rounded_rectangle((74,y-6,1726,y+57),radius=12,fill='#e8e4fb',outline=ACC,width=2)
 logo(im,94,y+1,42,logos.get(m['vendor'],'together.ai') if isnew else logos.get(m['vendor'], 'missing'))
 label=m['label'];text(d,(154,y+6),label,31,ACC if isnew else INK,isnew)
 if isnew:text(d,(690,y+10),'NEW',21,ACC,True)
 d.rounded_rectangle((1070,y+16,1400,y+36),radius=10,fill='#e6e6eb')
 d.rounded_rectangle((1070,y+16,1070+330*r['accuracy'],y+36),radius=10,fill=color)
 text(d,(925,y+6),f'{r["accuracy"]:.1%}',31,ACC if isnew else INK,isnew)
 text(d,(1510,y+6),f'{round(r["accuracy"]*949)} / 949',30,ACC if isnew else INK,isnew)
d.line((84,1214,1716,1214),fill=LINE,width=2)
text(d,(84,1243),'All models rescored on identical rows. 122 image-containing cases excluded.',27,MUTED)
text(d,(84,1285),'Historical runs; small score differences do not establish a winner. Tev1 confidence metrics unavailable.',25,MUTED)
text(d,(84,1340),'decisionbench.ai',28,bold=True);text(d,(1310,1340),'bench-v4 · September 2026',23,MUTED)
im.save(O/'tev1-thread.png')
print('Rendered tev1-reply.png and tev1-thread.png')
