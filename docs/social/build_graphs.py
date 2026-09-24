from pathlib import Path
import json, collections
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
R=Path(__file__).resolve().parents[2]; O=R/'docs/social'
models=[]
for p in (R/'results/bench-v4').glob('*/scores.json'):
 s=json.loads(p.read_text()); m=json.loads((p.parent/'metadata.json').read_text())
 models.append((m['model']['label'],s))
models.sort(key=lambda m:-m[1]['overall']['accuracy'])
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':14,'axes.spines.top':False,'axes.spines.right':False,'axes.spines.left':False,'axes.spines.bottom':False,'text.color':'#171717','axes.labelcolor':'#444444','xtick.color':'#555555','ytick.color':'#171717','savefig.facecolor':'#fafaf8','figure.facecolor':'#fafaf8','axes.facecolor':'#fafaf8'})
fig,axes=plt.subplots(1,2,figsize=(16,10),gridspec_kw={'width_ratios':[1.3,1]})
y=list(range(len(models)))
a=[s['overall']['accuracy']*100 for _,s in models]
lo=[v-s['overall']['wilson95'][0]*100 for v,(_,s) in zip(a,models)]
hi=[s['overall']['wilson95'][1]*100-v for v,(_,s) in zip(a,models)]
axes[0].errorbar(a,y,xerr=[lo,hi],fmt='o',color='#3028c8',capsize=4,markersize=8,elinewidth=2)
axes[0].set_yticks(y,[n for n,s in models]); axes[0].set_xlim(45,102);axes[0].set_xlabel('Accuracy (%) · Wilson 95% intervals',labelpad=15)
for i,v in enumerate(a):axes[0].annotate(f'{v:.1f}%',(v+hi[i]+1,i),va='center',fontsize=12)
lat=[s['latency_ms']['p50']/1000 for n,s in models]
axes[1].barh(y,lat,color='#3028c8',height=.48);axes[1].set_yticks(y,[]);axes[1].set_xlim(0,max(lat)*1.2);axes[1].set_xlabel('Median wall-clock seconds / decision',labelpad=15)
for i,v in enumerate(lat):axes[1].text(v+.06,i,f'{v:.2f}s',va='center',fontsize=13)
for ax in axes:ax.invert_yaxis();ax.grid(axis='x',color='#dededb',linewidth=.7);ax.set_axisbelow(True);ax.tick_params(axis='y',length=0,pad=12)
fig.text(.05,.94,'How much model does a decision need?',fontsize=29,weight='bold')
fig.text(.05,.893,'DECISION BENCH  /  1,071 cases · 35 tasks · 12 models',fontsize=15,color='#555555')
fig.subplots_adjust(left=.235,right=.95,top=.835,bottom=.18,wspace=.35)
fig.text(.05,.085,'Local published runs · bench-v4 · 23 Sep 2026. Invalid answers count as wrong.',fontsize=12,color='#555555')
fig.text(.05,.055,'Input modalities and provider setups differ. Latency includes overhead; overlapping intervals do not establish a winner.',fontsize=11,color='#555555')
fig.savefig(O/'accuracy-latency.png',dpi=150);plt.close(fig)
ids=['prd-1-53db8e9f2248657aa1000027','agt-4-hagrid-dev-1376-0','doc-2-is1009a.a.dialog-act.dharshi.131']
counts=collections.Counter(); total=collections.Counter()
for p in (R/'results/bench-v4').glob('*/predictions.jsonl'):
 for line in p.read_text().splitlines():
  r=json.loads(line)
  if r['row_id'] in ids:
   total[r['row_id']]+=1;counts[r['row_id']]+=not r['correct']
fig,ax=plt.subplots(figsize=(16,9));labels=['Headline A/B test','Citation support','Meeting action item']
ax.barh(range(3),[counts[k] for k in ids],color='#3028c8',height=.46)
ax.set_yticks(range(3),labels,fontsize=18);ax.invert_yaxis();ax.set_xlim(0,13.7);ax.set_xticks([0,3,6,9,12]);ax.grid(axis='x',color='#dededb');ax.set_axisbelow(True);ax.tick_params(axis='y',length=0,pad=18)
for i,k in enumerate(ids):ax.text(counts[k]+.18,i,f'{counts[k]}/{total[k]}',va='center',fontsize=22,weight='bold')
ax.set_xlabel('Models disagreeing with the recorded answer key',labelpad=20,fontsize=16)
fig.text(.06,.91,'Three cases that tripped models up',fontsize=30,weight='bold')
fig.text(.06,.85,'Selected examples · one case per task · not task-wide failure rates',fontsize=17,color='#555555')
fig.subplots_adjust(left=.25,right=.93,top=.75,bottom=.27)
fig.text(.06,.16,'Headline: all chose B; A had 1.52% CTR vs 0.71%. Models were not shown clicks or impressions.',fontsize=13)
fig.text(.06,.115,'Citation: 11 accepted an answer marked unsupported by HAGRID annotators.',fontsize=13)
fig.text(.06,.07,'Meeting: AMI labels an action item; 11 chose neither, 1 chose decision. Wording is ambiguous.',fontsize=13)
fig.savefig(O/'failure-examples.png',dpi=150);plt.close(fig)
(O/'failure-evidence.json').write_text(json.dumps({k:{'disagree':counts[k],'models':total[k]} for k in ids},indent=2))
print('Created accuracy-latency.png and failure-examples.png')
