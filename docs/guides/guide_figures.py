"""Real-value, static guide figures and local licensed font conversion."""
import json
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tmp/guide_libs'))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
from matplotlib.colors import ListedColormap, BoundaryNorm
from fontTools.ttLib import TTFont
import numpy as np

ASSETS=ROOT/'output/pdf/assets'
FONTS=ASSETS/'fonts'
FONTS.mkdir(parents=True,exist_ok=True)
for name in ['IBMPlexSans-Regular','IBMPlexSans-SemiBold','IBMPlexSansCondensed-Bold']:
    font=TTFont(ROOT/f'app/static/fonts/{name}.woff2')
    font.flavor=None
    font.save(FONTS/f'{name}.ttf')
    matplotlib.font_manager.fontManager.addfont(str(FONTS/f'{name}.ttf'))

plt.rcParams.update({'font.family':'IBM Plex Sans','font.size':11,'axes.labelcolor':'#172126','text.color':'#172126','axes.edgecolor':'#D8DEE3','axes.spines.top':False,'axes.spines.right':False,'axes.spines.left':False,'axes.spines.bottom':False,'xtick.color':'#59656F','ytick.color':'#59656F','grid.color':'#D8DEE3','grid.linewidth':.65,'savefig.facecolor':'white'})
data=json.loads((ASSETS/'guide_example.json').read_text(encoding='utf-8'))
COLORS=['#2457A6','#007A71','#925A08','#6A737D']
LABELS=['Striking priority','Grappling priority','Balanced priority']
MARKERS=['o','s','D']
DASHES=['-','--',':']

def save(fig,name):
    fig.savefig(ASSETS/(name+'.png'),dpi=220,bbox_inches='tight',pad_inches=.15)
    fig.savefig(ASSETS/(name+'.svg'),bbox_inches='tight',pad_inches=.15)
    plt.close(fig)

for key,title in [('neutral','Caso neutral'),('illustrative','Escenario hipotético de la interfaz')]:
    result=data[key]
    fig,ax=plt.subplots(figsize=(7.8,2.65))
    for i,row in enumerate(result['simulation']['summary']):
        ax.errorbar(row['expected_utility'],2-i,xerr=[[row['expected_utility']-row['lower_95']],[row['upper_95']-row['expected_utility']]],fmt=MARKERS[i],markersize=9,capsize=5,elinewidth=2,color=COLORS[i],label=LABELS[i])
        value=f"{100*row['expected_utility']:.2f}".replace('.',',')+' %'
        ax.text(.791,2-i,value,va='center',fontsize=11,fontweight='semibold')
    ax.axvline(result['baseline_probability'],color='#59656F',linestyle=':',linewidth=1.4)
    ax.text(result['baseline_probability'],2.55,'Baseline 68,58 %',ha='center',fontsize=10,color='#59656F')
    ax.set(yticks=[2,1,0],yticklabels=LABELS,xlim=(.58,.81),ylim=(-.45,2.85),xlabel='Probabilidad modelada de victoria')
    ax.xaxis.set_major_formatter(mtick.PercentFormatter(1,decimals=0))
    ax.grid(axis='x');ax.set_axisbelow(True)
    save(fig,key+'_intervals')

fig,ax=plt.subplots(figsize=(7.9,3.9))
rows=data['custom_resistance_sweep']
xs=[r['resistance'] for r in rows]
for i,label in enumerate(LABELS):
    ax.plot(xs,[r[label] for r in rows],DASHES[i],color=COLORS[i],linewidth=2.3,label=label)
for row in sorted(data['custom_resistance_thresholds'],key=lambda r:r['value']):
    ax.axvline(row['value'],color='#AEB9C2',linewidth=1)
ax.axvline(.5,color='#172126',linestyle='-.',linewidth=1)
ax.text(.5,.764,'Valor aplicado: 0,50',ha='center',fontsize=10)
ax.set(xlabel='Índice supuesto de resistencia del oponente',ylabel='Utilidad esperada central',xlim=(0,1),ylim=(.59,.78))
ax.yaxis.set_major_formatter(mtick.PercentFormatter(1,decimals=0));ax.grid(axis='y');ax.set_axisbelow(True)
ax.legend(loc='upper center',bbox_to_anchor=(.5,-.2),ncol=3,frameon=False,fontsize=10)
save(fig,'resistance_sensitivity')

grid=data['illustrative']['two_way']
xs=sorted(set(r['grappling_effect'] for r in grid));ys=sorted(set(r['resistance'] for r in grid))
ordered=sorted(grid,key=lambda r:(r['resistance'],r['grappling_effect']))
z=np.array([r['region'] for r in ordered]).reshape(len(ys),len(xs))
fig,ax=plt.subplots(figsize=(7.6,4.8))
ax.imshow(z,origin='lower',extent=[xs[0]-(xs[1]-xs[0])/2,xs[-1]+(xs[1]-xs[0])/2,ys[0]-(ys[1]-ys[0])/2,ys[-1]+(ys[1]-ys[0])/2],aspect='auto',cmap=ListedColormap(COLORS),norm=BoundaryNorm([-.5,.5,1.5,2.5,3.5],4),interpolation='nearest')
for j in range(0,len(ys),4):
    for i in range(0,len(xs),4):ax.text(xs[i],ys[j],['S','G','B','='][z[j,i]],ha='center',va='center',color='white',fontsize=9)
ax.scatter([.5],[.5],s=160,c='white',edgecolors='#172126',linewidths=2,zorder=5)
ax.annotate('Escenario aplicado',(.5,.5),xytext=(.03,.62),textcoords='data',fontsize=10,color='white',arrowprops={'arrowstyle':'-','color':'white','lw':1.2})
ax.set(xlabel='Efecto supuesto de grappling (log-odds)',ylabel='Resistencia supuesta del oponente',xlim=(-1.05,1.05),ylim=(-.02,1.02))
from matplotlib.patches import Patch
ax.legend(handles=[Patch(color=c,label=l) for c,l in zip(COLORS,['S · Striking','G · Grappling','B · Balanced','= · Sin preferencia'])],loc='upper center',bbox_to_anchor=(.5,-.2),ncol=2,frameon=False,fontsize=10)
save(fig,'decision_regions')

fig,ax=plt.subplots(figsize=(6.4,4.25))
cal=data['calibration']
ax.plot([0,1],[0,1],':',color='#59656F',label='Referencia ideal')
ax.errorbar([r['predicted'] for r in cal],[r['observed'] for r in cal],yerr=[[r['observed']-r['lower'] for r in cal],[r['upper']-r['observed'] for r in cal]],fmt='o-',color=COLORS[1],capsize=4,linewidth=1.5,label='527 combates de prueba')
for r in cal:ax.annotate('n='+str(r['n']),(r['predicted'],r['observed']),xytext=(5,6),textcoords='offset points',fontsize=8)
ax.set(xlim=(0,1),ylim=(0,1),xlabel='Probabilidad predicha media',ylabel='Fracción observada de victorias')
ax.xaxis.set_major_formatter(mtick.PercentFormatter(1,decimals=0));ax.yaxis.set_major_formatter(mtick.PercentFormatter(1,decimals=0));ax.grid();ax.legend(frameon=False,loc='lower right',fontsize=9)
save(fig,'calibration')
print('Converted three licensed fonts and generated five source-backed figure sets.')
