from pathlib import Path
import json, re
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
ROOT=Path(__file__).resolve().parents[2]
D=[
('Engineering','ENG', ['Find the file a fix changed','Classify a code change','Classify a vulnerability','Triage a secret-scanner alert','Match a diff to a commit']),
('AI agents & evals','AGT',['Select the right tool','Detect a hijacked agent','Check task completion','Verify citation support','Compare two replies']),
('Trust & safety','SAF',['Detect injections and jailbreaks','Classify toxic comments']),
('Customer support','SUP',['Route a complaint','Classify its issue']),
('Sales & commerce','COM',['Judge product relevance','Classify a product','Identify a company’s industry']),
('Finance','FIN',['Identify a 10-K section','Classify an 8-K event','Find a receipt total','Classify a financial amount']),
('Legal','LEG',['Check what an NDA entails','Classify a contract clause','Identify unfair terms','Detect a specified clause']),
('Product management','PRD',['Predict an A/B headline winner','Classify a version bump']),
('Data & analytics','DAT',['Select the right SQL query','Find an answer in a table','Check a chart against a claim','Infer a column’s value type']),
('Documents & meetings','DOC',['Classify a document page','Label decisions and action items','Match a summary to a meeting']),
('Design','DSN',['Identify an icon’s official name'])]
rows=[json.loads(l) for l in (ROOT/'data/corpus/bench-v4/cases.jsonl').read_text().splitlines()]
actual={r['task'] for r in rows}
expected={f'{prefix}-{i+1}' for _,prefix,tasks in D for i in range(len(tasks))}
assert expected==actual,(expected-actual,actual-expected)
assert len(D)==11 and sum(len(t) for _,_,t in D)==35
plt.rcParams.update({'font.family':'DejaVu Sans','text.color':'#171717','svg.fonttype':'none'})
fig=plt.figure(figsize=(16,17),facecolor='#fafaf8'); ax=fig.add_axes([0,0,1,1]);ax.set_xlim(0,1);ax.set_ylim(0,1);ax.axis('off')
ax.text(.045,.956,'DECISION BENCH',fontsize=17,color='#3028c8',weight='bold')
ax.text(.045,.910,'Small decisions. Across real work.',fontsize=31,weight='bold')
ax.text(.045,.868,'11 domains  /  35 tasks  /  1,071 source-backed cases',fontsize=18,color='#555555')
ax.text(.045,.825,'CLASSIFY    ROUTE    VERIFY    COMPARE    DETECT    LOCATE',fontsize=14,color='#3028c8',weight='bold')
for i,(name,prefix,tasks) in enumerate(D):
 col=i%3; row=i//3; x=.045+col*.309; top=.775-row*.176
 ax.add_patch(Rectangle((x,top-.154),.289,.154,facecolor='white',edgecolor='#dededb',linewidth=1))
 ax.add_patch(Rectangle((x,top-.005),.038,.005,facecolor='#3028c8',edgecolor='none'))
 ax.text(x+.014,top-.025,name,fontsize=15,weight='bold',va='top')
 ax.text(x+.268,top-.025,str(len(tasks)),fontsize=13,color='#3028c8',ha='right',va='top')
 for j,t in enumerate(tasks): ax.text(x+.014,top-.056-j*.018,t,fontsize=12.1,va='top')
x=.045+2*.309; top=.775-3*.176
ax.text(x+.014,top-.03,'Text, structured data & images',fontsize=14,weight='bold',va='top')
ax.text(x+.014,top-.065,'36 public source datasets\n122 cases with images\nReceipts · charts · pages · icons',fontsize=12.5,color='#555555',va='top',linespacing=1.7)
ax.text(.045,.049,'Each task asks a fixed question with a bounded set of answers.',fontsize=14,color='#555555')
ax.text(.045,.024,'decisionbench.ai   ·   Full task inventory, verified against the frozen corpus',fontsize=11,color='#555555')
for ext in ['png','svg']:fig.savefig(ROOT/f'docs/social/task-map.{ext}',dpi=150,facecolor=fig.get_facecolor())
(ROOT/'docs/social/task-map-data.json').write_text(json.dumps([{'domain':n,'task_ids':[f'{p}-{i+1}' for i in range(len(t))],'tasks':t} for n,p,t in D],indent=2))
print('Verified all 35 task IDs across 11 domains; generated task-map.png and .svg')
