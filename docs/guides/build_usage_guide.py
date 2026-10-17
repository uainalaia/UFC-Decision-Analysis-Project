"""Spanish, illustrated user guide. Requires the bundled document runtime.

First run prepare_guide_example.py with the project venv, then guide_figures.py
with the bundled Python. No application or model file is modified by this builder.
"""

import json
import math
import sys
from pathlib import Path
from html import escape

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tmp/guide_libs'))
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.colors import HexColor, Color, white
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import Paragraph, Table, TableStyle
from reportlab.lib.utils import ImageReader
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from PIL import Image

OUT = ROOT/'output/pdf'
A = OUT/'assets'
S = A/'screens'
R = ROOT/'reports/review_v2/after'
D = json.loads((A/'guide_example.json').read_text(encoding='utf-8'))
E,N = D['illustrative'],D['neutral']
SUM = E['simulation']['summary']
for name,file in [('Plex','IBMPlexSans-Regular'),('PlexBold','IBMPlexSans-SemiBold'),('PlexDisplay','IBMPlexSansCondensed-Bold')]:
    pdfmetrics.registerFont(TTFont(name,str(A/f'fonts/{file}.ttf')))
pdfmetrics.registerFontFamily('Plex',normal='Plex',bold='PlexBold',italic='Plex',boldItalic='PlexBold')

W,H = 595.276,841.89
M=46
CW=W-2*M
TEXT='#172126'; MUTED='#59656F'; BRAND='#882A3A'; LINE='#D8DEE3'; BG='#F3F5F7'
BLUE='#2457A6'; TEAL='#007A71'; OCHRE='#925A08'; GRAY='#6A737D'
styles = {
 'body':ParagraphStyle('body',fontName='Plex',fontSize=11,leading=15.5,textColor=HexColor(TEXT),spaceAfter=8),
 'small':ParagraphStyle('small',fontName='Plex',fontSize=9.2,leading=12.5,textColor=HexColor(MUTED)),
 'label':ParagraphStyle('label',fontName='PlexBold',fontSize=9,leading=12,textColor=HexColor(BRAND)),
 'h2':ParagraphStyle('h2',fontName='PlexBold',fontSize=16,leading=20,textColor=HexColor(TEXT)),
 'title':ParagraphStyle('title',fontName='PlexDisplay',fontSize=24,leading=27,textColor=HexColor(TEXT)),
 'cover':ParagraphStyle('cover',fontName='PlexDisplay',fontSize=32,leading=35,textColor=HexColor(TEXT)),
 'h3':ParagraphStyle('h3',fontName='PlexBold',fontSize=12,leading=16,textColor=HexColor(TEXT)),
 'table':ParagraphStyle('table',fontName='Plex',fontSize=9.5,leading=13,textColor=HexColor(TEXT)),
 'tablehead':ParagraphStyle('tablehead',fontName='PlexBold',fontSize=9.3,leading=12.5,textColor=HexColor(TEXT)),
}

OUTPUT=OUT/'MMA_Decision_Lab_Guia_Visual_de_Uso.pdf'
c=canvas.Canvas(str(OUTPUT),pagesize=(W,H),pageCompression=1)
c.setTitle('MMA Decision Lab | Guía visual de uso e interpretación')
c.setAuthor('MMA Decision Lab | documentación del prototipo académico')
c.setSubject('Paso a paso, lectura de resultados y guion de demostración en español')
PAGE=0
TRACE=[]

def txt(text,x,y,size=11,font='Plex',color=TEXT):
    c.setFillColor(HexColor(color));c.setFont(font,size);c.drawString(x,y,text)

def para(text,x,y,width=CW,style='body'):
    p=Paragraph(text,styles[style]);w,h=p.wrap(width,H)
    p.drawOn(c,x,y-h)
    TRACE.append((PAGE,'paragraph',round(y-h,2),round(y,2)))
    return y-h

def page(kicker,title,subtitle=None):
    global PAGE
    if PAGE:c.showPage()
    PAGE+=1
    c.bookmarkPage(f'p{PAGE}')
    c.addOutlineEntry(title,f'p{PAGE}',level=0,closed=False)
    c.setFillColor(white);c.rect(0,0,W,H,fill=1,stroke=0)
    txt('MMA DECISION LAB',M,H-30,9,'PlexBold',BRAND)
    c.setStrokeColor(HexColor(LINE));c.line(M,H-41,W-M,H-41)
    txt(kicker.upper(),M,H-67,9,'PlexBold',BRAND)
    y=para(title,M,H-82,style='cover' if PAGE==1 else 'title')
    if subtitle:y=para(subtitle,M,y-10,style='small')
    c.setStrokeColor(HexColor(LINE));c.line(M,39,W-M,39)
    txt('Guía visual | Interfaz v2 | 16 octubre 2026',M,24,8,'Plex',MUTED)
    c.setFont('PlexBold',9);c.setFillColor(HexColor(TEXT));c.drawRightString(W-M,24,f'{PAGE:02d} / 20')
    return y-20

def section(title,y):
    return para(title,M,y,style='h3')-9

def box(title,body,y,color=BRAND,bg=BG,height=None):
    p=Paragraph(body,styles['body']);_,ph=p.wrap(CW-36,H)
    h=height or ph+55
    c.setFillColor(HexColor(bg));c.roundRect(M,y-h,CW,h,8,fill=1,stroke=0)
    c.setFillColor(HexColor(color));c.roundRect(M,y-h,4,h,2,fill=1,stroke=0)
    txt(title,M+18,y-22,11,'PlexBold',color)
    p.drawOn(c,M+18,y-35-ph)
    TRACE.append((PAGE,'box',round(y-h,2),round(y,2)))
    return y-h-16

def bullets(items,y,width=CW,x=M):
    for item in items:
        c.setFillColor(HexColor(BRAND));c.circle(x+3,y-7,2,fill=1,stroke=0)
        y=para(item,x+14,y,width-14)-8
    return y

def steps(items,y):
    for n,(title,body) in enumerate(items,1):
        c.setFillColor(HexColor(BRAND));c.circle(M+12,y-11,11,fill=1,stroke=0)
        c.setFillColor(white);c.setFont('PlexBold',10);c.drawCentredString(M+12,y-14.5,str(n))
        y2=para('<b>'+title+'</b><br/>'+body,M+35,y,CW-35)
        y=min(y2,y-24)-13
    return y

def table(headers,rows,y,widths=None,fontstyle='table'):
    if widths is None:widths=[CW/len(headers)]*len(headers)
    data=[[Paragraph(escape(str(x)),styles['tablehead']) for x in headers]]
    data += [[Paragraph(str(x),styles[fontstyle]) for x in row] for row in rows]
    t=Table(data,colWidths=widths,repeatRows=1,hAlign='LEFT')
    t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),HexColor('#E8EDF1')),('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),10),('RIGHTPADDING',(0,0),(-1,-1),10),('TOPPADDING',(0,0),(-1,-1),8),('BOTTOMPADDING',(0,0),(-1,-1),8),('LINEBELOW',(0,0),(-1,-1),.5,HexColor(LINE)),('ROWBACKGROUNDS',(0,1),(-1,-1),[white,HexColor('#F8F9FA')])]))
    _,h=t.wrap(CW,H);t.drawOn(c,M,y-h)
    TRACE.append((PAGE,'table',round(y-h,2),round(y,2)))
    return y-h-16

def picture(path,x,y,width,height=None,crop=None,frame=True):
    """Clip the original screenshot in PDF space; the raster source stays unchanged."""
    im=Image.open(path);iw,ih=im.size
    if crop is None:crop=(0,0,iw,ih)
    cx,cy,cw,ch=crop
    h=height or width*ch/cw
    scale=width/cw
    c.saveState()
    clip=c.beginPath();clip.rect(x,y-h,width,h);c.clipPath(clip,stroke=0)
    c.drawImage(ImageReader(im),x-cx*scale,y-h-(ih-cy-ch)*scale,width=iw*scale,height=ih*scale,mask='auto')
    c.restoreState()
    if frame:
        c.setStrokeColor(HexColor(LINE));c.setLineWidth(.7);c.rect(x,y-h,width,h,fill=0,stroke=1)
    TRACE.append((PAGE,'image',round(y-h,2),round(y,2)))
    return y-h

def figure(name,y,height=None):
    im=Image.open(A/(name+'.png'))
    iw,ih=im.size
    scale=min(CW/iw,height/ih) if height else CW/iw
    w,h=iw*scale,ih*scale
    c.drawImage(ImageReader(im),M+(CW-w)/2,y-h,width=w,height=h,mask='auto')
    TRACE.append((PAGE,'figure',round(y-h,2),round(y,2)))
    return y-h-10

def pin(n,x,y):
    c.setFillColor(HexColor(BRAND));c.setStrokeColor(white);c.setLineWidth(2);c.circle(x,y,10,fill=1,stroke=1)
    c.setFillColor(white);c.setFont('PlexBold',9);c.drawCentredString(x,y-3,str(n))

def fmt(v,d=2):return f'{v:.{d}f}'.replace('.',',')
def pct(v,d=2):return fmt(v*100,d)+' %'
def pp(v,d=2):return ('+' if v>=0 else '')+fmt(v*100,d)+' pp'

# 01. Cover
y=page('Manual de usuario','Cómo usar y explicar\nMMA Decision Lab'.replace('\n','<br/>'),'Guía visual paso a paso | Español | Prototipo académico independiente')
y=para('De un combate histórico a una decisión táctica explicable.',M,y,CW,style='h3')-16
y=picture(S/'fight_brief.png',M,y,CW,crop=(278,65,1110,505))-14
y=para('Esta guía te enseña a <b>configurar el combate</b>, <b>leer la evidencia</b>, <b>comparar supuestos</b> y <b>presentar resultados con sus límites</b>. Conserva los nombres de los botones en inglés para que puedas encontrarlos en la interfaz.',M,y)-18
y=box('La idea central','El sistema explora qué ocurriría <b>dentro de un modelo y bajo supuestos explícitos</b>. Una probabilidad calculada no garantiza el resultado de un combate ni demuestra un efecto táctico causal.',y)
para('Ejemplo de trabajo: Khabib Nurmagomedov vs Conor McGregor, antes del 6 de octubre de 2018. Snapshot congelado: greco-5e38ebeb9bb8.',M,y,style='small')

# 02. route
y=page('Ruta de aprendizaje','Tu primera demostración, de principio a fin','Los números de página son enlaces internos. Puedes volver a este mapa desde los marcadores del PDF.')
routes=[('01','Fight brief','Confirma combate, focal y fecha.',4),('02','Fighter evidence','Compara historia anterior y sus muestras.',5),('03','Tactical model','Define prioridades y aplica supuestos.',6),('04','Outcome analysis','Ejecuta y lee resultados vigentes.',9),('05','Sensitivity','Cambia supuestos y busca estabilidad.',12),('06','Research report','Guarda el registro coherente.',16)]
for num,title,desc,target in routes:
    c.setFillColor(HexColor(BG));c.roundRect(M,y-62,CW,62,6,fill=1,stroke=0)
    txt(num,M+14,y-25,18,'PlexDisplay',BRAND)
    txt(title,M+52,y-22,12,'PlexBold')
    para(desc,M+52,y-31,CW-105,style='small')
    txt(str(target),W-M-27,y-25,11,'PlexBold',BRAND)
    c.linkRect('',f'p{target}',(M,y-62,W-M,y),relative=0,thickness=0)
    y-=73
y=para('<b>Dos apoyos que puedes abrir en cualquier momento:</b><br/><b>Validation</b> (p. 14): qué respaldo tiene el baseline.<br/><b>Methodology</b> (p. 17): definiciones, fuentes, ecuaciones y límites.',M,y)-12
box('Recomendación para aprender','Primero ejecuta el caso neutral. Después usa el preset ilustrativo y compara. Así verás qué parte proviene de la historia y qué parte cambia al introducir supuestos.',y)

# 03. evidence origins
y=page('Antes de usarlo','Distingue cuatro orígenes de información','Esta distinción evita la mayoría de las interpretaciones incorrectas.')
origins=[('OBSERVADO','Lo registrado','Fechas, resultados, acciones y exposición de combates retenidos. Ejemplo: 10 combates anteriores para cada peleador.',BLUE),('ESTIMADO','Desde la historia','Perfiles derivados y baseline logístico. Ejemplo: 68,58 % para el peleador focal con el modelo guardado.',TEAL),('SUPUESTO','Lo que tú propones','Asignaciones, efectos tácticos, resistencia, costo y distribuciones de incertidumbre. No son efectos estimados de una intervención.',OCHRE),('CALCULADO','Salida del modelo','Utilidades, bandas, diferencias pareadas, regret y sensibilidad. Dependen de los datos, del baseline y de los supuestos.',BRAND)]
for label,title,body,color in origins:
    c.setFillColor(HexColor(color));c.roundRect(M,y-92,112,92,6,fill=1,stroke=0)
    txt(label,M+13,y-29,10,'PlexBold','#FFFFFF');txt(title,M+13,y-50,10,'Plex','#FFFFFF')
    para(body,M+130,y-12,CW-130)
    y-=109
y=section('El recorrido lógico',y)
nodes=[('Historia anterior','Perfiles'),('Baseline','Probabilidad inicial'),('Supuestos','Escenarios'),('Cálculo','Comparación')]
for i,(a,b) in enumerate(nodes):
    x=M+i*128
    c.setFillColor(HexColor(BG));c.roundRect(x,y-58,116,58,5,fill=1,stroke=0)
    txt(a,x+9,y-21,10,'PlexBold');txt(b,x+9,y-39,8.3,'Plex',MUTED)
    if i<3:txt('>',x+119,y-31,11,'PlexBold',BRAND)
y-=80
box('Frase útil al explicarlo','"La historia informa el punto de partida; nosotros declaramos los efectos tácticos que queremos explorar; el sistema calcula las consecuencias de esos supuestos."',y)

# 04. setup
y=page('Paso 01 | Fight brief','Abre el sistema y fija el combate','Todo resultado se refiere al peleador A, llamado Focal fighter.')
y=para('En PowerShell, abre la carpeta del proyecto y ejecuta <b>.\\run.ps1</b>. Después entra en <link href="http://127.0.0.1:8501/" color="#882A3A">http://127.0.0.1:8501/</link>. Si la aplicación ya está abierta, empieza en Fight brief.',M,y)-13
y=picture(S/'matchup_editor.png',M,y,CW,crop=(284,178,1098,610))-12
y=steps([('Pulsa Change matchup.','Elige Historical bout o Custom matchup. Comprueba quién será Fighter A y quién será Opponent.'),('Confirma el corte y la fuente.','Para el ejemplo: 2018-10-06, Lightweight, 5 rounds y Historical model. Solo contribuyen fechas estrictamente anteriores; se excluye todo el día del combate.'),('Pulsa Apply matchup.','Cancel matchup edits descarta el borrador. Un baseline histórico exige al menos dos combates anteriores retenidos por peleador y última división registrada compatible.')],y)
para('<b>Scenario-only:</b> el baseline se introduce manualmente y es un supuesto. Si cambias el corte y no hay modelo preparado, Outcome analysis ofrece Prepare historical baseline; el cálculo no se dispara al abrir un selector.',M,y,style='small')

# 05. profiles
y=page('Paso 02 | Fighter evidence','Lee evidencia histórica comparable','Describe a los peleadores antes del corte; no atribuye causalidad táctica.')
y=picture(R/'fighter_evidence_1440.png',M,y,CW,crop=(284,296,1098,596))-12
y=table(['Métrica del ejemplo','Khabib','Conor'],[['Golpes significativos conectados / minuto','4,34','5,82'],['Golpes significativos recibidos / minuto','1,55','4,55'],['Derribos conectados / 15 minutos','5,44','0,92'],['Exposición observada (minutos)','135,20','81,30'],['Combates anteriores retenidos','10','10']],y,[307,98,98])
y=bullets(['Compara <b>la misma fila y unidad</b>. Una tasa por minuto no equivale a un total ni a una tasa por 15 minutos.','En golpes recibidos, una cifra mayor no se interpreta automáticamente como mejor. Las diferencias descriptivas no prueban una ventaja táctica.','No observations significa ausencia de información utilizable, incluido 0/0; no significa una habilidad medida de cero. Los porcentajes etiquetados Smoothed usan el suavizado documentado.'],y)
para('Abre Inspect contributing bouts and denominators para ver qué combates, fechas y exposiciones contribuyen. El registro retenido no es necesariamente toda la carrera profesional.',M,y,style='small')

# 06. policies
y=page('Paso 03 | Tactical model','Qué significan las tres prioridades','Las barras representan oportunidades planeadas, no tiempo real garantizado dentro del combate.')
phases=[('Standing','#46525C'),('Clinch','#7A8791'),('Ground','#BBC3CB')]
allocations=[('Striking priority',[.75,.15,.10]),('Grappling priority',[.20,.30,.50]),('Balanced priority',[.45,.25,.30])]
for name,values in allocations:
    txt(name,M,y-13,13,'PlexBold');y-=31
    x=M
    for (label,color),v in zip(phases,values):
        c.setFillColor(HexColor(color));c.rect(x,y-21,CW*v,21,fill=1,stroke=0);x+=CW*v
    para(' | '.join(f'{label}: {int(v*100)} %' for (label,_),v in zip(phases,values)),M,y-29,style='small')
    y-=68
y=box('Balanced no es una política adaptativa','Balanced priority mantiene la asignación fija 45/25/30. No aprende a cambiar de táctica durante la pelea. La referencia matemática 50/25/25 es distinta de Balanced y tampoco es un perfil observado.',y,color=OCHRE)
y=section('Cómo se calcula el árbol',y)
tree=[('Decisión','Prioridad táctica'),('Respuesta','Resistencia rival'),('Resultado','Victoria o derrota'),('Utilidad','1 o 0')]
for i,(top,bottom) in enumerate(tree):
    x=M+i*128;c.setFillColor(HexColor(BG));c.roundRect(x,y-60,116,60,5,fill=1,stroke=0)
    txt(top,x+9,y-21,10,'PlexBold');txt(bottom,x+9,y-42,8.3,'Plex',MUTED)
    if i<3:txt('>',x+119,y-35,11,'PlexBold',BRAND)
y-=82
y=para('El motor combina tres respuestas del oponente y dos desenlaces por respuesta. Como victoria vale 1 y derrota vale 0, <b>la utilidad esperada equivale a la probabilidad de victoria dentro del modelo</b>.',M,y)-12
y=para('En Applied decision tree elige Tree alternative y abre la tabla de ramas. Los pesos de respuesta del oponente son un trío distinto de los porcentajes Standing/Clinch/Ground.',M,y,style='small')-8
para('Ejemplo central neutral: 0,25 × p0 + 0,50 × p0 + 0,25 × p0 = p0. Las ramas de derrota aportan cero a la utilidad, porque derrota vale 0.',M,y,style='small')

# 07. editor
y=page('Paso 04 | Edit assumptions','Introduce supuestos, luego aplícalos','Escribir un valor crea un borrador. No cambia el cálculo aplicado hasta pulsar Apply assumptions.')
y=picture(S/'basic_parameters.png',M,y,CW,crop=(284,308,1098,370))-12
y=table(['Control visible','Cómo interpretarlo'],[['Striking effect (log-odds)','Coeficiente supuesto para el énfasis de pie. 0,35 no significa +35 % ni +35 puntos porcentuales.'],['Grappling effect (log-odds)','Coeficiente supuesto de grappling, modulado por la resistencia del oponente y la asignación relativa.'],['Opponent resistance index','Índice de escenario entre 0 y 1. No es la tasa histórica de defensa de derribos del peleador.'],['Counter-exposure cost (log-odds)','Penalización supuesta por exposición al contraataque; no es una frecuencia observada de derrotas.']],y,[194,CW-194])
y=para('<b>Para aprender:</b> pulsa Use neutral assumptions y aplica. Para el segundo recorrido, pulsa <b>Use illustrative assumptions</b> y luego <b>Apply assumptions</b>. Cancel assumption edits vuelve a los valores aplicados.',M,y)-12
para('<b>Preset de la interfaz usado en esta guía:</b> s=0,35; g=0,50; resistencia=0,50; costo=0,10; semiancho=0,15; concentración=30; respuestas 25/50/25. Todos son hipotéticos. Otros ejemplos guardados del proyecto pueden usar valores distintos.',M,y,style='small')

# 08 uncertainty
y=page('Paso 04 | Uncertainty','No confundas tres tipos de incertidumbre','Abre Opponent response and uncertainty para declarar la parte hipotética del escenario.')
y=picture(S/'assumption_editor.png',M,y,CW,crop=(284,132,1098,466))-12
y=table(['Origen','Qué ocurre','Qué significa'],[['Baseline empírico','64 modelos bootstrap, condicionados al diseño y C elegidos.','Aproximan incertidumbre de parámetros; no abarcan todas las limitaciones del modelo.'],['Supuestos tácticos','Efectos triangulares y, opcionalmente, pesos Dirichlet.','Representan el rango de supuestos que declaras. Un semiancho mayor amplía ese rango.'],['Error Monte Carlo','Integración con semilla y número de draws.','Más draws pueden reducir error numérico; no añaden combates ni validan los supuestos.']],y,[105,193,CW-298])
y=para('<b>Dos tríos distintos:</b> las asignaciones tácticas dicen dónde se planean oportunidades; las probabilidades 25/50/25 dicen cuánto pesa cada respuesta rival. Estas últimas deben sumar 1 y ser positivas si activas Dirichlet.',M,y)-10
y=para('En este modelo, la aleatoriedad victoria/derrota se integra analíticamente. Las distribuciones de utilidad no son histogramas de peleas futuras ganadas o perdidas. Para neutralidad exacta usa s=g=c=0 y semiancho=0.',M,y,style='small')-16
for i,(label,value,weight) in enumerate([('Lower resistance','0,25','25 %'),('Expected resistance','0,50','50 %'),('Stronger resistance','0,75','25 %')]):
    x=M+i*(CW+12)/3
    c.setFillColor(HexColor(BG));c.roundRect(x,y-56,(CW-24)/3,56,5,fill=1,stroke=0)
    txt(label,x+9,y-19,9,'PlexBold')
    txt('Índice '+value+' | peso '+weight,x+9,y-39,8.3,'Plex',MUTED)
y-=68
para('Ejemplo con R=0,50: el motor usa R-0,25, R y R+0,25, limitados a 0-1. Una concentración Dirichlet mayor reduce la variación de los pesos alrededor del trío declarado.',M,y,style='small')

# 09 neutral
y=page('Paso 05 | Outcome analysis','Primero ejecuta el caso neutral','En Tactical model: Use neutral assumptions > Apply assumptions. Después abre Outcome analysis.')
y=steps([('Revisa el contexto y Neutral effects.','Confirma el focal, el corte temporal y que no existan cambios pendientes que quieras aplicar.'),('Abre Calculation settings si lo necesitas.','Para reproducir esta guía: Integration draws = 5000 y Random seed = 422. Son ajustes computacionales, no tamaño de muestra histórica.'),('Pulsa Run analysis.','Espera la actividad real y comprueba Calculated · current analysis. El motor impide envíos duplicados durante el cálculo.')],y)
y=figure('neutral_intervals',y,height=220)
y=box('Lectura correcta del empate',f'Las tres alternativas tienen la misma media integrada: <b>{pct(N["simulation"]["summary"][0]["expected_utility"])}</b>, la misma banda y diferencia pareada cero. Cada una recibe aproximadamente <b>33,3 % de rank-first share</b>. No existe un líder táctico único.',y,color=GRAY)
para('El baseline puntual es 68,58 %. La media de sus draws bootstrap es aproximadamente 68,79 % en esta ejecución. Esa diferencia numérica no es un efecto táctico: con neutralidad, cada alternativa comparte el mismo baseline en cada draw.',M,y,style='small')

# 10 result chart
y=page('Interpretación 01','Cómo leer medias y bandas','Segundo recorrido: aplica el preset ilustrativo de la interfaz y ejecuta con 5000 draws, semilla 422.')
y=figure('illustrative_intervals',y,height=220)
y=table(['Prioridad','Media','Banda central 95 %'],[[r['policy'],pct(r['expected_utility']),pct(r['lower_95'])+' a '+pct(r['upper_95'])] for r in SUM],y,[183,97,CW-280])
y=bullets(['<b>El punto</b> es la media de utilidad esperada al integrar los parámetros y supuestos del análisis.','<b>La banda central del 95 %</b> resume los percentiles 2,5 y 97,5 de esa distribución de utilidad. No es un intervalo causal ni una garantía sobre una pelea concreta.','<b>La línea del baseline</b> es la estimación puntual histórica. Las diferencias pareadas de la tabla usan draws compartidos, no una resta obligatoria contra esa línea.','Si dos bandas se superponen, no concluyas por ese solo hecho que las alternativas son iguales. Consulta las diferencias pareadas.'],y)
box('Mayor media no implica preferencia robusta',f'Striking priority tiene la mayor media ({pct(SUM[0]["expected_utility"])}), pero la conclusión completa sigue siendo <b>No robust tactical preference</b>. El siguiente paso es entender los criterios y comprobar sensibilidad.',y)

# 11 paired metrics
y=page('Interpretación 02','Diferencias, rank-first y regret','pp significa puntos porcentuales. Es una unidad de diferencia entre probabilidades.')
paired_baseline=SUM[0]['expected_utility']-SUM[0]['difference_from_baseline']
y=box('Ejemplo: la diferencia contra el baseline pareado',f'<b>{pct(SUM[0]["expected_utility"])} - {pct(paired_baseline)} ≈ {pp(SUM[0]["difference_from_baseline"])}</b><br/>El cálculo usa cifras sin redondear. El segundo valor es la media del baseline de los mismos draws. Restar el baseline puntual 68,58 % daría otra cifra, porque son resúmenes distintos. +1,57 pp no significa +1,57 % de mejora relativa.',y,color=BLUE)
pair=E['simulation']['pairwise'][1]
y=table(['Comparación pareada','Media A - B','Banda central 95 %'],[['Striking - Balanced',pp(pair['mean_difference']),pp(pair['lower_95'])+' a '+pp(pair['upper_95'])],['Striking - Grappling',pp(E['simulation']['pairwise'][0]['mean_difference']),pp(E['simulation']['pairwise'][0]['lower_95'])+' a '+pp(E['simulation']['pairwise'][0]['upper_95'])]],y,[178,110,CW-288])
y=section('Rank-first share: ganar la comparación del modelo',y)
y=para(f'En este escenario, Striking ocupa el primer lugar en <b>{pct(SUM[0]["rank_first_share"],1)}</b> de los draws. Eso describe este conjunto de supuestos y su incertidumbre. <b>No significa 100 % de probabilidad de ganar el combate ni certeza de que striking sea la mejor táctica real.</b>',M,y)-16
y=section('Expected regret: costo de no elegir el mejor del draw',y)
y=para(f'Grappling tiene regret esperado de <b>{fmt(SUM[1]["expected_regret"]*100)} pp</b>; Balanced, <b>{fmt(SUM[2]["expected_regret"]*100)} pp</b>. Es la utilidad media que se deja de obtener frente a la mejor alternativa dentro del mismo draw. Menor es mejor dentro del modelo.',M,y)-16
y=section('MC standard error y desviaciones controladas',y)
y=para('MC standard error mide precisión numérica de la integración; no valida el modelo. Empirical-only SD y Scenario-only SD son comparaciones controladas de incertidumbre: no se suman como una descomposición exacta de la varianza total.',M,y)-16
y=section('Dos paneles para profundizar',y)
bullets(['<b>Uncertainty distributions and controlled comparisons:</b> compara centro, dispersión y solapamiento de las distribuciones. No representan frecuencias de victorias futuras.','<b>Convergence and reproducibility:</b> compara medias con 500, 2500 y 5000 draws del mismo flujo. Una curva estable indica estabilidad numérica; no valida datos ni supuestos. Aquí también ves ID, contexto y configuración.'],y)

# 12 one-way
y=page('Paso 06 | Sensitivity','Pregunta qué cambia al variar un supuesto','Ejemplo personalizado: resistencia del oponente entre 0 y 1; los demás valores centrales quedan fijos.')
y=para('En One assumption at a time selecciona <b>Opponent resistance index</b>; introduce One-way minimum = <b>0</b> y maximum = <b>1</b>; pulsa <b>Apply one-way range</b>. La línea vertical señala el valor aplicado 0,50.',M,y)-14
y=figure('resistance_sensitivity',y,height=270)
roots=sorted(D['custom_resistance_thresholds'],key=lambda r:r['value'])
y=table(['Resistencia aproximada','Cambio de mayor utilidad central'],[[fmt(r['value'],4),r['from_policy']+' > '+r['to_policy']] for r in roots],y,[155,CW-155])
y=para('Estos cruces muestran dónde cambia la alternativa con mayor utilidad <b>central</b> dentro del rango. No son umbrales de habilidad real ni prueban una preferencia robusta bajo incertidumbre.',M,y)-12
para('Si aparece No top-ranking crossover, solo significa que no se encontró un cambio de líder dentro de ese rango. Los valores de un formulario se guardan al enviarlo; no prometas conservar ediciones que todavía no has enviado. Descarga el CSV de la exploración si quieres conservarla.',M,y,style='small')

# 13 regions
y=page('Paso 06 | Decision regions','Cómo leer el mapa de decisiones','Eje horizontal: efecto supuesto de grappling. Eje vertical: resistencia supuesta. El círculo es el escenario aplicado.')
y=para('En Decision regions usa Horizontal assumption = <b>Grappling effect</b>, rango <b>-1 a 1</b>; Vertical assumption = <b>Opponent resistance index</b>, rango <b>0 a 1</b>; 25 puntos por eje. Pulsa <b>Apply decision-region ranges</b>.',M,y)-12
y=figure('decision_regions',y,height=330)
y=bullets(['<b>S, G y B</b> identifican categorías; el color no representa intensidad ni certeza. Las letras ayudan a leer el mapa sin depender del color.','Un punto recibe una categoría cuando su ventaja central sobre la segunda alternativa supera <b>1 pp</b>. <b>=</b> indica que no supera ese margen; no significa dato ausente.','Una región azul alrededor del punto actual no basta para una preferencia robusta. El criterio completo también revisa baseline, diferencias pareadas e inestabilidad en la cuadrícula declarada.'],y)
y=para('La cuadrícula es un conjunto finito de escenarios deterministas. No cubre todas las tácticas, parámetros o modelos posibles. El tornado complementario mide el margen de una política de referencia; en un empate, esa referencia no representa un líder único.',M,y,style='small')-12
para('Abre Reference-policy sensitivity in the analysis record para leer el tornado: cada fila varía un supuesto entre sus extremos por defecto y muestra el margen de la referencia frente a su mejor competidora. Un margen negativo indica que la referencia queda por detrás; un recorrido amplio señala sensibilidad a ese supuesto.',M,y,style='small')

# 14 validation
y=page('Validation','Por qué el baseline sigue siendo exploratorio','La calidad de predicción y la plausibilidad de un supuesto táctico son preguntas diferentes.')
y=figure('calibration',y,height=270)
y=table(['Prueba histórica','Valor','Lectura'],[['Combates de prueba','527','Bloque cronológico separado del ajuste.'],['Brier score','0,2425 vs 0,2500','Menor es mejor; la ventaja observada es modesta.'],['Log loss','0,6781 vs 0,6931','Menor es mejor para probabilidades.'],['Accuracy','57,1 %','Métrica secundaria; no es la confianza en esta pelea.'],['Diferencia de Brier, intervalo 95 %','-0,01620 a +0,00077','Incluye cero: el criterio de soporte no se cumple.']],y,[137,124,CW-261])
y=para('<b>Calibración:</b> compara probabilidades medias predichas con fracciones observadas. La diagonal es la referencia ideal; las barras son intervalos Wilson y n es el número de combates por grupo. Un grupo pequeño puede ser muy incierto.',M,y)-10
para('La evaluación no certifica calibración perfecta. El bootstrap por combate no captura toda la dependencia entre peleadores; el archivo retrospectivo puede contener correcciones posteriores. Data quality permite inspeccionar exclusiones y valores ausentes.',M,y,style='small')

# 15 robustness & states
y=page('Interpretación 03','Qué significa No robust tactical preference','Es una conclusión válida y útil: el criterio completo no respalda una preferencia robusta para esa configuración.')
checks=[('1','Soporte del baseline','NO','El intervalo de mejora de Brier incluye cero.',BRAND),('2','Ventaja pareada suficiente','SÍ',f'Límite inferior mínimo: {fmt(E["recommendation"]["paired_lower_95"]*100,3)} pp; supera 1 pp más el margen de error MC.',TEAL),('3','Estabilidad en toda la cuadrícula','NO','La misma alternativa no lidera toda la cuadrícula por defecto.',BRAND)]
for n,title,status,body,color in checks:
    c.setFillColor(HexColor(BG));c.roundRect(M,y-72,CW,72,6,fill=1,stroke=0)
    txt(n,M+14,y-26,20,'PlexDisplay',color);txt(title,M+44,y-25,12,'PlexBold');txt(status,W-M-39,y-25,11,'PlexBold',color)
    para(body,M+44,y-39,CW-65,style='small');y-=84
y=box('Conclusión del ejemplo','Striking lidera las medias y los draws de este escenario, pero fallan dos requisitos del criterio completo. Explica el resultado como una <b>preferencia condicional del escenario que no alcanza robustez</b>, sin presentarla como una prescripción demostrada.',y)
y=section('Comprueba además el estado del registro',y)
table(['Estado visible','Qué hacer'],[['Sin resultado','Run analysis para la configuración aplicada.'],['Unapplied changes','Aplica o cancela el borrador; las otras vistas usan lo aplicado.'],['Inputs changed / previous analysis','Recalcula. El registro anterior pertenece a sus propios inputs.'],['Calculated · current analysis','Puedes leer y exportar el registro vigente.'],['Error de ejecución','Corrige el problema y reintenta; el último válido se conserva como anterior.']],y,[195,CW-195])

# 16 report
y=page('Paso 07 | Research report','Exporta una explicación que pueda reproducirse','Genera el informe después de confirmar el resultado vigente y sus supuestos.')
reportshot=S/'report_downloads.png'
if not reportshot.exists():reportshot=R/'research_report_ready_1440.png'
y=picture(reportshot,M,y,CW,crop=(284,408,1098,333))-13
y=steps([('Abre Research report y revisa el contexto.','Comprueba focal, oponente, corte, fuente de baseline, semilla, draws y conclusión.'),('Pulsa Generate research report.','La aplicación congela una copia coherente del análisis. Si cambias inputs después, las descargas previas se identifican como anteriores.'),('Elige el formato adecuado.','HTML para leer y presentar sin conexión; CSV para resultados; JSON para configuración y metadatos; ZIP para el registro reproducible completo.')],y)
y=table(['Formato','Contenido principal'],[['HTML','Contexto, interpretación, tablas, gráficos, fuentes y límites; recursos esenciales incrustados.'],['CSV / JSON','El CSV conserva valores numéricos; muchas probabilidades están en 0-1. El JSON guarda contexto, parámetros, versiones y resúmenes.'],['ZIP','HTML y JSON; CSV de políticas, diferencias pareadas, convergencia, árbol, one-way, two-way y tornado.']],y,[100,CW-100])
para('<b>Atención al alcance:</b> el informe principal conserva el barrido por defecto de grappling y la cuadrícula grappling/resistencia. La exploración personalizada de resistencia de la p. 12 se guarda mediante su propio CSV; no sustituye silenciosamente el criterio de robustez del informe.',M,y,style='small')

# 17 advanced
y=page('Opciones de apoyo','Datos propios, metodología y recuperación','Son rutas avanzadas; no necesitas importar archivos para realizar la primera demostración.')
y=section('Importar un snapshot compatible',y)
y=para('En <b>Validation > Data quality > Import a compatible research snapshot</b>, carga los cuatro archivos CSV compatibles, con los nombres indicados. El límite es 12 MB por archivo. No basta una tabla genérica con nombres y victorias: se exige el esquema de origen.',M,y)-12
y=table(['Archivos requeridos'],[['ufc_event_details.csv'],['ufc_fighter_details.csv'],['ufc_fight_results.csv'],['ufc_fight_stats.csv']],y,[CW])
y=box('Aplicar una fuente cambia todo el vínculo','Pulsa Validate and apply snapshot solo con una fuente compatible. La validación conserva los criterios de calidad. Al aplicar un snapshot nuevo se eliminan los resultados, modelos preparados y exportaciones anteriores de la sesión. Restore frozen research snapshot vuelve a la fuente original.',y,color=OCHRE)
y=section('Usa Methodology para explicar el alcance',y)
y=bullets(['Localiza definiciones, ecuaciones, versiones, fuentes y procedencia de parámetros.','El baseline implementado es <b>logístico regularizado</b>. No atribuyas al aplicativo el modelo Markov completo de la literatura si no está implementado.','Balanced es una asignación estática; las alternativas no son etiquetas tácticas observadas ni tratamientos causales identificados.'],y)
para('Si el histórico es insuficiente, cambia el combate/corte o usa Scenario-only con un baseline explícitamente asumido. Si faltan recursos locales, sigue el estado Research resources unavailable y las instrucciones del README. No sustituyas un error por una cifra inventada.',M,y,style='small')

# 18 presentation script
y=page('Para explicarlo en voz alta','Guion de demostración de unos tres minutos','Puedes adaptarlo a una clase, una reunión de investigación o una presentación del proyecto.')
script=[('1. Qué pregunta responde','"MMA Decision Lab compara tres prioridades tácticas estáticas para un peleador focal. Su objetivo es mostrar cómo cambia una decisión al variar supuestos explícitos."'),('2. De dónde sale el punto de partida','"En este ejemplo analizamos a Khabib frente a Conor antes del 6 de octubre de 2018. Cada perfil usa diez combates anteriores retenidos. La probabilidad base del modelo es aproximadamente 68,58 %."'),('3. Qué decidimos nosotros','"Las asignaciones y los efectos tácticos son supuestos. Primero ejecuto efectos neutrales: las alternativas empatan. Después aplico el escenario ilustrativo y lo identifico como hipotético."'),('4. Qué muestra el cálculo',f'"En ese escenario, striking tiene media {pct(SUM[0]["expected_utility"])}. La banda describe incertidumbre en la utilidad bajo el modelo. La diferencia contra el baseline pareado es {pp(SUM[0]["difference_from_baseline"])}; no es un efecto causal medido."'),('5. Por qué no proclamamos una táctica ganadora','"Aunque striking lidera todos los draws de este escenario, el baseline sigue siendo exploratorio y la preferencia no sobrevive toda la cuadrícula de sensibilidad. Por eso el sistema mantiene No robust tactical preference."'),('6. Qué puede revisar la audiencia','"Podemos inspeccionar combates, parámetros, validación, diferencias y sensibilidad; finalmente exportar un registro con semilla y configuración. La utilidad del sistema es hacer visible el razonamiento y sus límites."')]
for title,body in script:
    y=para(title,M,y,style='h3')-6
    y=para(body,M,y)-16
para('Si te piden una conclusión de una frase: "Este escenario favorece una alternativa dentro del modelo, pero la evidencia y el análisis de estabilidad todavía no justifican una preferencia táctica robusta."',M,y,style='small')

# 19 glossary
y=page('Diccionario rápido','Qué significa cada etiqueta en inglés','Conserva estos significados cuando expliques el sistema.')
terms=[('Focal fighter / Fighter A','Peleador cuya probabilidad y utilidad estás analizando; importa el orden A/B.'),('Information cutoff','Fecha límite: solo se utiliza historia estrictamente anterior.'),('Baseline / p0','Probabilidad inicial estimada, o asumida si eliges Scenario-only.'),('Expected utility','Media de utilidad; con victoria=1 y derrota=0 equivale a P(victoria) dentro del modelo.'),('Central 95% band','Percentiles centrales de la distribución de utilidad bajo parámetros y supuestos.'),('Paired difference','Diferencia entre alternativas calculadas con los mismos draws.'),('Percentage points / pp','Diferencia absoluta entre porcentajes; pasar de 68 % a 70 % son +2 pp.'),('Rank-first share','Fracción de draws en que una alternativa ocupa el primer lugar; empates repartidos.'),('Expected regret','Pérdida media de utilidad frente a la mejor alternativa de cada draw.'),('Bootstrap','Aproximación de incertidumbre de parámetros mediante remuestreo y ajuste.'),('Dirichlet concentration','Control de dispersión del vector de pesos de respuesta; menor concentración implica más variación.'),('Log-odds effect','Coeficiente en la escala del modelo; no se interpreta directamente como porcentaje.'),('Integration draws / seed','Número de integraciones y semilla para reproducirlas; no son combates históricos.'),('Robust preference','Preferencia que supera los criterios declarados de soporte, margen pareado y estabilidad.')]
table(['Etiqueta','Interpretación práctica'],terms,y,[172,CW-172])

# 20 checklist and provenance
y=page('Antes de presentar','Lista de control y procedencia de esta guía','Una explicación clara necesita tanto pasos correctos como límites visibles.')
y=bullets(['<b>Contexto:</b> confirma A/B, fecha, división y rounds. Explica la exclusión del día del combate.','<b>Origen:</b> diferencia observado, estimado, supuesto y calculado; identifica Historical model o Scenario-only.','<b>Aplicación:</b> comprueba Apply/Cancel y cambios pendientes. No leas un resultado anterior como si fuera vigente.','<b>Cálculo:</b> registra semilla e iteraciones. Interpreta media, banda y comparaciones pareadas con sus unidades.','<b>Soporte:</b> enseña Validation y Sensitivity antes de afirmar robustez. Conserva No robust preference cuando corresponda.','<b>Registro:</b> exporta la configuración vigente y el CSV específico de cualquier exploración personalizada.'],y)
y=table(['Evita decir','Di en su lugar'],[['"El sistema demuestra que striking gana."','"El escenario supone ciertos efectos y calcula una utilidad mayor para striking."'],['"100 % rank-first equivale a victoria segura."','"Lidera los draws de este modelo; su P(victoria) y su soporte son otras magnitudes."'],['"5000 simulaciones son 5000 peleas nuevas."','"Son integraciones de incertidumbre con los datos ya disponibles."']],y,[221,CW-221])
y=section('Cómo se construyó el material',y)
y=para('Capturas reales de la interfaz v2 y gráficos estáticos calculados con el motor existente. Ejemplo histórico: Khabib Nurmagomedov vs Conor McGregor, corte 2018-10-06; snapshot greco-5e38ebeb9bb8; modelo científico 0.1.0; 5000 draws y semilla 422. El preset hipotético es el de la interfaz, especificado en la p. 7.',M,y,style='small')-12
y=para('Fuentes de esta guía: controles implementados en app/, metodología y model card del repositorio, evaluación persistida y registro guide_example.json. Las cifras se redondean para lectura; el registro conserva precisión numérica. Los gráficos de resistencia de la p. 12 son una exploración personalizada, separada de la cuadrícula por defecto.',M,y,style='small')-12
para('Prototipo académico independiente, sin respaldo implícito de UFC ni de autores citados. La guía no añade evidencia causal ni certifica calibración. Para abrir el sistema usa .\\run.ps1 y http://127.0.0.1:8501/.',M,y,style='small')

assert PAGE==20
below=[row for row in TRACE if row[2]<60]
if below:
    raise RuntimeError('Page content enters footer: '+str(below))
c.save()
(A/'layout_trace.json').write_text(json.dumps({'pages':PAGE,'blocks':TRACE,'output':OUTPUT.relative_to(ROOT).as_posix()},indent=2),encoding='utf-8')
print(OUTPUT)
print('20 pages generated; no tracked text/image/table blocks enter the footer.')
