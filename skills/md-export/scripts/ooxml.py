# /// script
# requires-python = ">=3.10"
# dependencies = ["python-docx", "pdfplumber"]
# ///
"""Reference generation and OOXML postprocessing; all implementation is original."""
from __future__ import annotations
import copy
from pathlib import Path
import zipfile
from lxml import etree as ET
from docx import Document
from docx.enum.style import WD_STYLE_TYPE
from docx.enum.section import WD_ORIENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm
from presets import PAPER_MM, spacing

NS={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main','m':'http://schemas.openxmlformats.org/officeDocument/2006/math','r':'http://schemas.openxmlformats.org/officeDocument/2006/relationships'}
THEME_FONTS=('asciiTheme','hAnsiTheme','eastAsiaTheme','cstheme','csTheme')


def el(tag, **attrs):
    node=OxmlElement('w:'+tag)
    for k,v in attrs.items(): node.set(qn('w:'+k),str(v))
    return node


def child(parent, tag):
    node=parent.find(qn('w:'+tag))
    if node is None:
        node=el(tag); parent.append(node)
    return node


def replace(parent,tag,**attrs):
    for node in parent.findall(qn('w:'+tag)): parent.remove(node)
    node=el(tag,**attrs); parent.append(node)
    return node


def clean(root):
    for n in root.iter(qn('w:rFonts')):
        for k in THEME_FONTS: n.attrib.pop(qn('w:'+k),None)
    for n in root.iter(qn('w:color')):
        n.attrib.clear(); n.set(qn('w:val'),'000000')
    # Style italics only. Authored emphasis in document.xml is retained.
    for style in root.iter(qn('w:style')):
        for n in list(style.iter(qn('w:i')))+list(style.iter(qn('w:iCs'))): n.getparent().remove(n)
        r=child(style,'rPr'); replace(r,'color',val='000000')


def set_rpr(r,s):
    replace(r,'rFonts',ascii=s['ascii'],hAnsi=s['ascii'],cs=s['ascii'],eastAsia=s['eastAsia'])
    replace(r,'sz',val=round(s['size']*2)); replace(r,'szCs',val=round(s['size']*2))
    replace(r,'b',val=int(s['bold'])); replace(r,'bCs',val=int(s['bold']))
    replace(r,'i',val=0); replace(r,'iCs',val=0)
    replace(r,'color',val='000000')
    replace(r,'u',val='single' if s['underline'] else 'none')
    for n in r.findall(qn('w:shd')): r.remove(n)


def set_ppr(p,s):
    kind,value=spacing(s['line_spacing'])
    replace(p,'jc',val=s['alignment'])
    replace(p,'spacing',before=round(s['space_before']*20),after=round(s['space_after']*20),line=round(value*(20 if kind=='fixed' else 240)),lineRule='exact' if kind=='fixed' else 'auto')
    replace(p,'ind',firstLineChars=round(s['first_line_chars']*100),firstLine=round(s['first_line_chars']*s['size']*20),leftChars=round(s['left_chars']*100),left=round(s['left_chars']*s['size']*20),right=0)
    replace(p,'keepNext',val=int(s['keep_next']))
    replace(p,'snapToGrid',val=int(s['snap_to_grid']))
    for n in p.findall(qn('w:shd')): p.remove(n)
    if s['shading']: replace(p,'shd',val='clear',fill=s['shading'],color='auto')


def style_id(doc,name): return doc.styles[name].style_id


def add_numbering(doc,p):
    kind=p['numbering']['kind']
    if kind=='none': return None
    root=doc.part.numbering_part.element
    aid=max([int(n.get(qn('w:abstractNumId'))) for n in root.findall(qn('w:abstractNum'))]+[-1])+1
    nid=max([int(n.get(qn('w:numId'))) for n in root.findall(qn('w:num'))]+[0])+1
    abstract=el('abstractNum',abstractNumId=aid)
    abstract.append(el('multiLevelType',val='multilevel'))
    formats=['decimal']*3 if kind=='academic' else ['chineseCounting','chineseCounting','decimal','decimal']
    texts=['%1','%1.%2','%1.%2.%3'] if kind=='academic' else ['%1、','（%2）','%3.','（%4）']
    for i,(fmt,text) in enumerate(zip(formats,texts)):
        lvl=el('lvl',ilvl=i)
        for node in [el('start',val=1),el('numFmt',val=fmt),el('lvlText',val=text),el('pStyle',val=style_id(doc,'Heading '+str(i+1))),el('suff',val='space' if kind=='academic' else 'nothing'),el('lvlJc',val='left')]: lvl.append(node)
        if i: lvl.append(el('lvlRestart',val=i))
        rp=child(lvl,'rPr'); set_rpr(rp,p['styles']['Heading '+str(i+1)])
        abstract.append(lvl)
        np=replace(child(doc.styles['Heading '+str(i+1)].element,'pPr'),'numPr')
        np.append(el('ilvl',val=i)); np.append(el('numId',val=nid))
    root.append(abstract)
    num=el('num',numId=nid); num.append(el('abstractNumId',val=aid)); root.append(num)
    return nid


def build_reference(default,path,p):
    doc=Document(default)
    clean(doc.styles.element)
    for style in doc.styles:
        fonts=child(child(style.element,'rPr'),'rFonts')
        for attr,key in [('ascii','ascii'),('hAnsi','ascii'),('cs','ascii'),('eastAsia','eastAsia')]:
            if not fonts.get(qn('w:'+attr)): fonts.set(qn('w:'+attr),p['styles']['Normal'][key])
    defaults=child(doc.styles.element,'docDefaults')
    set_rpr(child(child(defaults,'rPrDefault'),'rPr'),p['styles']['Normal'])
    set_ppr(child(child(defaults,'pPrDefault'),'pPr'),p['styles']['Normal'])
    for name,s in p['styles'].items():
        if name not in doc.styles:
            typ=WD_STYLE_TYPE.CHARACTER if name in ('Verbatim Char','Hyperlink','Footnote Reference') else WD_STYLE_TYPE.TABLE if name=='Table' else WD_STYLE_TYPE.PARAGRAPH
            doc.styles.add_style(name,typ)
        style=doc.styles[name]
        style.base_style=None
        set_rpr(child(style.element,'rPr'),s)
        if style.type!=WD_STYLE_TYPE.CHARACTER: set_ppr(child(style.element,'pPr'),s)
        if name.startswith('Heading '): replace(child(style.element,'pPr'),'outlineLvl',val=int(name.split()[-1])-1)
        # Remove default table conditional formatting before defining ours.
        if name=='Table':
            for n in style.element.findall(qn('w:tblStylePr')): style.element.remove(n)
    add_numbering(doc,p)
    page=p['page']; section=doc.sections[0]
    w,h=PAPER_MM[page['paper_size']]
    if page['orientation']=='landscape': w,h=h,w
    section.orientation=WD_ORIENT.LANDSCAPE if page['orientation']=='landscape' else WD_ORIENT.PORTRAIT
    section.page_width=Cm(w/10); section.page_height=Cm(h/10)
    t,b,l,r=page['margins_cm']
    section.top_margin=Cm(t); section.bottom_margin=Cm(b); section.left_margin=Cm(l); section.right_margin=Cm(r)
    section.footer_distance=Cm(max(0,b-p['page_numbers']['distance_from_body_cm']))
    replace(section._sectPr,'docGrid',type='lines' if page['grid_line_pitch'] else 'default',linePitch=page['grid_line_pitch'] or 360)
    odd_even=p['page_numbers']['kind']=='odd_even'
    doc.settings.odd_and_even_pages_header_footer=odd_even
    for footer,alignment in [(section.footer,'right' if odd_even else 'center')]+([(section.even_page_footer,'left')] if odd_even else []):
        para=footer.paragraphs[0]; para.style=doc.styles['Page Number']
        replace(child(para._p,'pPr'),'jc',val=alignment)
        if odd_even:
            replace(child(para._p,'pPr'),'ind',left=round(14*20),right=round(14*20),firstLine=0,firstLineChars=0)
        if odd_even: para.add_run('— ')
        field=el('fldSimple',instr='PAGE')
        run=el('r'); set_rpr(child(run,'rPr'),p['styles']['Page Number'])
        txt=el('t'); txt.text='1'; run.append(txt); field.append(run); para._p.append(field)
        if odd_even: para.add_run(' —')
    doc.save(path)


def read_package(path):
    with zipfile.ZipFile(path) as z: return {name:z.read(name) for name in z.namelist()}


def xml_parts(package):
    return {name:ET.fromstring(data) for name,data in package.items() if name.startswith('word/') and name.endswith('.xml')}


def write_package(path,package,parts):
    merged=dict(package)
    for name,tree in parts.items(): merged[name]=ET.tostring(tree,xml_declaration=True,encoding='UTF-8',standalone=True)
    staged=Path(path).with_suffix('.zip.tmp')
    try:
        with zipfile.ZipFile(staged,'w',zipfile.ZIP_DEFLATED) as z:
            for name,data in merged.items(): z.writestr(name,data)
        staged.replace(path)
    finally: staged.unlink(missing_ok=True)


def ptext(p): return ''.join(n.text or '' for n in p.iter(qn('w:t')))


def pstyle(p):
    node=p.find('w:pPr/w:pStyle',NS)
    return node.get(qn('w:val')) if node is not None else 'Normal'


def table_headers(table):
    rows=table.findall('w:tr',NS); count=0
    for row in rows:
        n=row.find('w:trPr/w:tblHeader',NS)
        if n is None or n.get(qn('w:val'),'1') in ('0','false','off'): break
        count+=1
    return rows,count


def table_borders(table,kind):
    for cell in table.findall('w:tr/w:tc',NS):
        props=child(cell,'tcPr')
        for node in props.findall(qn('w:tcBorders')): props.remove(node)
    borders=replace(child(table,'tblPr'),'tblBorders')
    for edge in ('top','left','bottom','right','insideH','insideV') if kind=='grid' else ('top','bottom'):
        borders.append(el(edge,val='single',sz=4 if kind=='grid' else 12,color='000000',space=0))
    rows,head_count=table_headers(table)
    if kind=='three_line' and head_count and len(rows)>1:
        for cell in rows[head_count-1].findall('w:tc',NS): child(child(cell,'tcPr'),'tcBorders').append(el('bottom',val='single',sz=6,color='000000',space=0))


def paragraph_layout(para,name,preset):
    """Shared image/math exceptions; authored body/heading styles stay intact."""
    math=para.find('.//m:oMath',NS) is not None
    standalone=not ptext(para).strip() and not name.startswith('Heading ')
    reason=None
    if standalone and not math and para.find('.//w:drawing',NS) is not None:
        name='Captioned Figure' if name=='Captioned Figure' else 'Figure'
        reason='standalone_image'
    elif standalone and para.find('.//m:oMathPara',NS) is not None:
        name='Display Math'; reason='display_math'
    style=preset['styles'].get(name)
    if style is None: return name,None
    kind,value=spacing(style['line_spacing'])
    if math and kind=='fixed':
        return name,dict(reason='omml',line_spacing=f'at_least:{value:g}')
    if reason: return name,dict(reason=reason,line_spacing=style['line_spacing'])
    return name,None


def postprocess(path,p,heading_flags):
    # Pandoc rebuilds numbering.xml; restore definitions using IDs free in output.
    if p['numbering']['kind']!='none':
        doc=Document(path); add_numbering(doc,p); doc.save(path)
    package=read_package(path); parts=xml_parts(package); root=parts['word/document.xml']
    styles=parts['word/styles.xml']
    ids={n.find('w:name',NS).get(qn('w:val')):n.get(qn('w:styleId')) for n in styles.findall('w:style',NS) if n.find('w:name',NS) is not None}
    # python-docx stores built-in style names in lower case in OOXML.
    ids.update({n:next((v for k,v in ids.items() if k.casefold()==n.casefold()),n.replace(' ','')) for n in p['styles']})
    heading_index=0
    for para in root.iter(qn('w:p')):
        sid=pstyle(para)
        if sid in [ids['Heading '+str(i)] for i in range(1,10)]:
            if heading_index<len(heading_flags) and heading_flags[heading_index]['disabled']:
                np=replace(child(para,'pPr'),'numPr'); np.append(el('numId',val=0))
            heading_index+=1
        if sid==ids['Table Caption']: replace(child(para,'pPr'),'keepNext',val=1)
        if sid==ids['Source Code']:
            # Pandoc uses Verbatim Char for block runs too; its body-sized font
            # belongs only to inline code. Blocks inherit Source Code's 10pt.
            for ref in para.findall('.//w:rPr/w:rStyle',NS):
                if ref.get(qn('w:val'))==ids['Verbatim Char']: ref.getparent().remove(ref)
    for table in root.iter(qn('w:tbl')):
        table_borders(table,p['table']['kind'])
        rows,head_count=table_headers(table)
        for idx,row in enumerate(rows):
            for cell in row.findall('w:tc',NS):
                for para in cell.findall('w:p',NS):
                    replace(child(para,'pPr'),'pStyle',val=ids['Table Text'])
                    if idx<head_count:
                        for run in para.iter(qn('w:r')):
                            replace(child(run,'rPr'),'b',val=1); replace(child(run,'rPr'),'bCs',val=1)
    # Apply exceptions after table styles have their final values.
    for para in root.iter(qn('w:p')):
        sid=pstyle(para)
        name=next((name for name in p['styles'] if ids[name]==sid),'Normal')
        layout_name,exception=paragraph_layout(para,name,p)
        if layout_name!=name: replace(child(para,'pPr'),'pStyle',val=ids[layout_name])
        if exception and exception['line_spacing'].startswith('at_least:'):
            value=float(exception['line_spacing'].split(':')[1])
            # Keep before/after and all other authored paragraph properties.
            space=child(child(para,'pPr'),'spacing')
            space.set(qn('w:line'),str(round(value*20))); space.set(qn('w:lineRule'),'atLeast')
    footer_fallback=False
    if p['page_numbers']['kind']=='odd_even':
        even=root.find('.//w:footerReference[@w:type="even"]',NS)
        flag=parts['word/settings.xml'].find('w:evenAndOddHeaders',NS)
        if even is None or flag is None or flag.get(qn('w:val'),'1')=='0':
            footer_fallback=True
            for name,tree in parts.items():
                if name.startswith('word/footer'):
                    for para in tree.iter(qn('w:p')): replace(child(para,'pPr'),'jc',val='center')
    for name,tree in parts.items(): clean(tree)
    write_package(path,package,parts)
    return footer_fallback
