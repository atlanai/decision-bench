from pathlib import Path
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
R=Path(__file__).resolve().parents[2];O=R/'docs/social'
plt.rcParams.update({'font.family':'DejaVu Sans','text.color':'#171717','axes.labelcolor':'#444444','xtick.color':'#666666','ytick.color':'#666666','svg.fonttype':'none'})
fig,ax=plt.subplots(figsize=(16,10),facecolor='#fafaf8');ax.set_facecolor('#fafaf8')
fig.subplots_adjust(left=.10,right=.95,top=.77,bottom=.19)
fig.text(.065,.935,'Accuracy vs. response time',fontsize=32,weight='bold')
fig.text(.065,.89,'One dot per model. Higher is more accurate. Further left is faster.',fontsize=18,color='#555555')
fig.text(.065,.837,'Jev: 93.8% accuracy at 437 ms median latency',fontsize=18,color='#3028c8',weight='bold')
ax.set_xlim(0,4.2);ax.set_ylim(48,103)
ax.set_xticks([0,1,2,3,4],['0','1 s','2 s','3 s','4 s']);ax.set_yticks([50,60,70,80,90,100],[f'{v}%' for v in [50,60,70,80,90,100]])
ax.set_xlabel('Median time per decision  →  slower',fontsize=15,labelpad=14);ax.set_ylabel('Accuracy  →  higher',fontsize=15,labelpad=18)
ax.tick_params(labelsize=13,length=0,pad=8);ax.grid(color='#e4e4df',linewidth=.8);ax.set_axisbelow(True)
for sp in ax.spines.values():sp.set_visible(False)
# Hand-placed direct labels avoid overlap while thin leaders retain exact positions.
labels={
'jev-1.13':(.16,87.0,'Jev 1.13','left'),
'qwen3-32b':(.15,76.0,'Qwen3-32B','left'),
'nova-micro-v1':(.84,65.5,'Amazon Nova Micro','left'),
'laya-routed':(1.66,53.0,'Laya (routed)','left'),
'deepseek-v4.1-flash':(.96,98.5,'DeepSeek V4.1 Flash','left'),
'gpt-5.6-luna':(1.48,85.5,'GPT-5.6 Luna','left'),
'gpt-6-luna':(2.03,101.0,'GPT-6 Luna','left'),
'glm-5.3-flash':(2.43,86.0,'GLM 5.3 Flash','left'),
'claude-haiku-4.5':(2.04,78.5,'Claude Haiku 4.5','left'),
'gemini-flash-lite-latest':(3.13,101.0,'Gemini Flash Lite','left'),
'gemini-3.5-flash':(3.72,96.8,'Gemini 3.5\nFlash','left'),
'claude-sonnet-5':(3.23,84.5,'Claude Sonnet 5','left')}
for m in json.loads((O/'adjusted-metrics.json').read_text()):
 id=m['id'];x=m['latency']['p50']/1000;y=m['accuracy']*100
 s={'overall':{'wilson95':m['wilson']}}
 color='#3028c8' if id=='jev-1.13' else '#7d8394'
 lo,hi=[v*100 for v in s['overall']['wilson95']]
 ax.vlines(x,lo,hi,color=color,alpha=.42,lw=1.2)
 ax.scatter(x,y,s=150 if id=='jev-1.13' else 70,color=color,edgecolor='white',linewidth=1,zorder=4)
 tx,ty,name,ha=labels[id]
 ax.annotate(name,(x,y),xytext=(tx,ty),fontsize=12.5,color=color if id=='jev-1.13' else '#363a45',weight='bold' if id=='jev-1.13' else 'normal',ha=ha,va='center',arrowprops={'arrowstyle':'-','color':color,'lw':.8},zorder=5)
ax.annotate('BETTER',(0.08,101),fontsize=10,color='#3028c8',weight='bold')
fig.text(.065,.097,'12 models · eligible rows only · vertical whiskers: 95% accuracy intervals.',fontsize=11,color='#626262')
fig.text(.065,.063,'Jev: 1,041 scored cases; 30 image-only cases excluded. Model denominators and input modalities differ.',fontsize=11,color='#626262')
for ext in ['png','svg']:fig.savefig(O/f'accuracy-speed.{ext}',dpi=150,facecolor=fig.get_facecolor())
print('Generated accuracy-speed.png and .svg from scores.json')
