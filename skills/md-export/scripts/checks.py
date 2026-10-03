# /// script
# requires-python = ">=3.10"
# dependencies = ["python-docx", "pdfplumber"]
# ///
"""Effective OOXML values and PDF glyph/content verification for generated structures."""
from __future__ import annotations
import re
from collections import Counter
import pdfplumber
from docx.oxml.ns import qn
from ooxml import NS, THEME_FONTS, read_package, xml_parts, pstyle, ptext, table_headers, paragraph_layout
from presets import PAPER_MM, spacing

RUN_FIELDS=('ascii','eastAsia','size','bold','italic','color','underline')
PARA_FIELDS=('alignment','line_spacing','space_before','space_after','first_line_chars','left_chars','keep_next','snap_to_grid','shading')


def truth(n): return n is not None and n.get(qn('w:val'),'1') not in ('0','false','off')


def norm(text): return re.sub(r'\s+','',text or '')


def is_cjk(char): return bool(re.match(r'[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff\U00020000-\U0003134f]',char))


def properties(node):
    out={}
    if node is None: return out
    fonts=node.find('w:rFonts',NS)
    if fonts is not None:
        for f in ('ascii','eastAsia'):
            if fonts.get(qn('w:'+f)): out[f]=fonts.get(qn('w:'+f))
    for tag,key in [('sz','size'),('color','color'),('jc','alignment')]:
        n=node.find('w:'+tag,NS)
        if n is not None:
            value=n.get(qn('w:val'))
            out[key]=float(value)/2 if key=='size' else value
    for tag,key in [('b','bold'),('i','italic'),('keepNext','keep_next'),('snapToGrid','snap_to_grid')]:
        n=node.find('w:'+tag,NS)
        if n is not None: out[key]=truth(n)
    n=node.find('w:u',NS)
    if n is not None: out['underline']=n.get(qn('w:val'),'single')!='none'
    n=node.find('w:shd',NS)
    if n is not None: out['shading']=n.get(qn('w:fill'))
    n=node.find('w:spacing',NS)
    if n is not None:
        for a,k in [('before','space_before'),('after','space_after')]:
            if n.get(qn('w:'+a)) is not None: out[k]=float(n.get(qn('w:'+a)))/20
        if n.get(qn('w:line')):
            kind='fixed' if n.get(qn('w:lineRule'))=='exact' else 'multiple' if n.get(qn('w:lineRule'),'auto')=='auto' else 'at_least'
            out['line_spacing']=f'{kind}:{float(n.get(qn("w:line")))/(20 if kind!="multiple" else 240):g}'
    n=node.find('w:ind',NS)
    if n is not None:
        for a,k in [('firstLineChars','first_line_chars'),('leftChars','left_chars')]:
            if n.get(qn('w:'+a)) is not None: out[k]=float(n.get(qn('w:'+a)))/100
        if n.get(qn('w:firstLineChars')) is None and n.get(qn('w:firstLine'))=='0': out['first_line_chars']=0
        if n.get(qn('w:hanging')) is not None: out['hanging_pt']=float(n.get(qn('w:hanging')))/20
    return out


class Resolver:
    """Scope: generated Pandoc/reference structures, not arbitrary Word layout."""
    def __init__(self,parts):
        self.parts=parts
        root=parts['word/styles.xml']
        self.styles={n.get(qn('w:styleId')):n for n in root.findall('w:style',NS)}
        self.names={sid:n.find('w:name',NS).get(qn('w:val')) for sid,n in self.styles.items() if n.find('w:name',NS) is not None}
        self.default_r=root.find('w:docDefaults/w:rPrDefault/w:rPr',NS)
        self.default_p=root.find('w:docDefaults/w:pPrDefault/w:pPr',NS)
        self.numbering=parts.get('word/numbering.xml')

    def chain(self,sid):
        found=[]; seen=set()
        while sid:
            if sid in seen or sid not in self.styles: raise ValueError('未支持的样式或 basedOn 环: '+sid)
            seen.add(sid); node=self.styles[sid]; found.insert(0,(sid,node))
            base=node.find('w:basedOn',NS); sid=base.get(qn('w:val')) if base is not None else None
        return found

    @staticmethod
    def apply(values,sources,props,source,toggle=False):
        for k,v in props.items():
            if toggle and k in ('bold','italic'):
                if v:
                    values[k]=not values.get(k,False); sources[k]=source
                continue
            values[k]=v; sources[k]=source

    def style(self,sid):
        values=dict(bold=False,italic=False,underline=False,shading=None,keep_next=False,snap_to_grid=False,first_line_chars=0,left_chars=0,space_before=0,space_after=0)
        sources={k:'OOXML default' for k in values}
        for node in (self.default_p,self.default_r): self.apply(values,sources,properties(node),'docDefaults')
        for name,node in self.chain(sid):
            for tag in ('pPr','rPr'): self.apply(values,sources,properties(node.find('w:'+tag,NS)),'style:'+name,toggle=tag=='rPr')
        return values,sources

    def number_level(self,para):
        np=para.find('w:pPr/w:numPr',NS)
        ilvl=None; nid=None
        for sid,node in self.chain(pstyle(para)):
            n=node.find('w:pPr/w:numPr',NS)
            if n is not None:
                level=n.find('w:ilvl',NS); num=n.find('w:numId',NS)
                if level is not None: ilvl=int(level.get(qn('w:val')))
                if num is not None: nid=int(num.get(qn('w:val')))
        if np is not None:
            level=np.find('w:ilvl',NS); num=np.find('w:numId',NS)
            if level is not None: ilvl=int(level.get(qn('w:val')))
            if num is not None: nid=int(num.get(qn('w:val')))
        if not nid or self.numbering is None: return None
        num=self.numbering.find(f'w:num[@w:numId="{nid}"]',NS)
        if num is None: return None
        override=num.find(f'w:lvlOverride[@w:ilvl="{ilvl or 0}"]/w:lvl',NS)
        if override is not None: return override
        aid=num.find('w:abstractNumId',NS)
        if aid is None: return None
        return self.numbering.find(f'w:abstractNum[@w:abstractNumId="{aid.get(qn("w:val"))}"]/w:lvl[@w:ilvl="{ilvl or 0}"]',NS)

    def effective(self,para,run=None):
        values=dict(bold=False,italic=False,underline=False,shading=None,keep_next=False,snap_to_grid=False,first_line_chars=0,left_chars=0,space_before=0,space_after=0)
        sources={k:'OOXML default' for k in values}
        for node in (self.default_p,self.default_r): self.apply(values,sources,properties(node),'docDefaults')
        table=next((a for a in para.iterancestors() if a.tag==qn('w:tbl')),None)
        if table is not None:
            ref=table.find('w:tblPr/w:tblStyle',NS)
            if ref is not None:
                for sid,node in self.chain(ref.get(qn('w:val'))):
                    for tag in ('pPr','rPr'): self.apply(values,sources,properties(node.find('w:'+tag,NS)),'table style:'+sid,toggle=tag=='rPr')
                    rows,heads=table_headers(table)
                    row=next((a for a in para.iterancestors() if a.tag==qn('w:tr')),None)
                    cell=next((a for a in para.iterancestors() if a.tag==qn('w:tc')),None)
                    cells=row.findall('w:tc',NS) if row is not None else []
                    conditions=['wholeTable']
                    if row in rows:
                        idx=rows.index(row)
                        conditions+=['band1Horz' if idx%2==0 else 'band2Horz']
                        if idx<heads: conditions+=['firstRow']
                        if idx==len(rows)-1: conditions+=['lastRow']
                    if cell in cells:
                        idx=cells.index(cell)
                        conditions+=['band1Vert' if idx%2==0 else 'band2Vert']
                        if idx==0: conditions+=['firstCol']
                        if idx==len(cells)-1: conditions+=['lastCol']
                    for condition in conditions:
                        for cond in node.findall(f'w:tblStylePr[@w:type="{condition}"]',NS):
                            for tag in ('pPr','rPr'): self.apply(values,sources,properties(cond.find('w:'+tag,NS)),f'table condition:{condition}',toggle=tag=='rPr')
        for sid,node in self.chain(pstyle(para)):
            for tag in ('pPr','rPr'): self.apply(values,sources,properties(node.find('w:'+tag,NS)),'style:'+sid,toggle=tag=='rPr')
        lvl=self.number_level(para)
        if lvl is not None:
            for tag in ('pPr','rPr'):
                # Number glyph rPr does not apply to the following text run.
                if tag=='pPr' or run is None: self.apply(values,sources,properties(lvl.find('w:'+tag,NS)),'numbering level',toggle=False)
        self.apply(values,sources,properties(para.find('w:pPr',NS)),'paragraph direct')
        if run is not None:
            ref=run.find('w:rPr/w:rStyle',NS)
            if ref is not None:
                for sid,node in self.chain(ref.get(qn('w:val'))): self.apply(values,sources,properties(node.find('w:rPr',NS)),'character style:'+sid,toggle=True)
            self.apply(values,sources,properties(run.find('w:rPr',NS)),'run direct')
        return values,sources


def color_scan(parts):
    failures=[]
    for name,root in parts.items():
        for node in root.iter(qn('w:color')):
            if node.get(qn('w:val'))!='000000' or any(qn('w:'+k) in node.attrib for k in ('themeColor','themeTint','themeShade')):
                failures.append(f'{name}: 非黑色或主题文字颜色 {dict(node.attrib)}')
        for node in root.iter(qn('w:rFonts')):
            if any(qn('w:'+k) in node.attrib for k in THEME_FONTS): failures.append(f'{name}: 主题字体属性')
    return failures


def status(rows):
    if any(r['status']=='fail' for r in rows): return 'fail'
    if any(r['status']=='unknown' for r in rows): return 'unknown'
    return 'pass'


def row(location,required,docx=None,pdf=None,state='pass',details=None):
    result=dict(location=location,required=required,docx=docx,pdf=pdf,status=state)
    if details: result['details']=details
    return result


def same(key,a,b):
    if key=='line_spacing':
        if a==b: return True
        try: return spacing(a)==spacing(b)
        except ValueError: return False
    if isinstance(a,(float,int)) and not isinstance(a,bool): return b is not None and abs(a-b)<0.03
    return a==b


def expected_for_run(resolver,para,run,preset):
    name=resolver.names.get(pstyle(para),'Normal')
    name=next((n for n in preset['styles'] if n.casefold()==name.casefold()),None)
    if name is None: return None
    s=dict(preset['styles'][name])
    table=next((a for a in para.iterancestors() if a.tag==qn('w:tbl')),None)
    if table is not None:
        rows,heads=table_headers(table)
        tr=next((a for a in para.iterancestors() if a.tag==qn('w:tr')),None)
        if tr in rows[:heads]: s['bold']=True
    char=run.find('w:rPr/w:rStyle',NS)
    if char is not None:
        sid=char.get(qn('w:val')); charname=resolver.names.get(sid)
        cname=next((n for n in preset['styles'] if n.casefold()==str(charname).casefold()),None)
        if cname in ('Hyperlink','Verbatim Char','Footnote Reference'):
            for k in RUN_FIELDS:
                if name=='Source Code' and cname=='Verbatim Char': continue
                if k in ('bold','italic'):
                    if preset['styles'][cname][k]: s[k]=not s[k]
                else: s[k]=preset['styles'][cname][k]
        else: return None
    # Authored emphasis is direct formatting, not a preset violation.
    direct=properties(run.find('w:rPr',NS))
    for k in ('bold','italic'):
        if k=='bold' and table is not None and tr in rows[:heads]: continue
        if k in direct: s[k]=direct[k]
    return s


def check_docx(path,preset,heading_flags=None):
    parts=xml_parts(read_package(path)); resolver=Resolver(parts); checks=[]; paragraphs=[]; exceptions=[]
    for message in color_scan(parts): checks.append(row('文字颜色/主题属性','全部黑色，无主题属性',state='fail',details=message))
    if not color_scan(parts): checks.append(row('文字颜色/主题属性','全部黑色，无主题属性',state='pass'))
    root=parts['word/document.xml']
    note_numbers={}
    for kind in ('footnote','endnote'):
        ids=list(dict.fromkeys(n.get(qn('w:id')) for n in root.iter(qn('w:'+kind+'Reference'))))
        note_numbers[kind]={nid:str(i+1) for i,nid in enumerate(ids)}
    used=Counter(pstyle(p) for tree in parts.values() for p in tree.iter(qn('w:p')))
    used.update(n.get(qn('w:val')) for tree in parts.values() for tag in ('rStyle','tblStyle') for n in tree.iter(qn('w:'+tag)))
    for name,required in preset['styles'].items():
        sid=next((s for s,n in resolver.names.items() if n.casefold()==name.casefold()),None)
        if sid is None:
            checks.append(row('样式/'+name,required,state='fail',details='缺少生成样式')); continue
        got,sources=resolver.style(sid)
        font_node=resolver.styles[sid].find('w:rPr/w:rFonts',NS)
        fonts_ok=font_node is not None and all(font_node.get(qn('w:'+k))==required['eastAsia' if k=='eastAsia' else 'ascii'] for k in ('ascii','hAnsi','cs','eastAsia'))
        fields=RUN_FIELDS if resolver.styles[sid].get(qn('w:type'))=='character' else RUN_FIELDS+PARA_FIELDS
        errors={k:dict(expected=required[k],actual=got.get(k)) for k in fields if not same(k,required[k],got.get(k))}
        if not fonts_ok: errors['rFonts']='缺少四个显式字体属性，或值不符'
        checks.append(row('样式/'+name,required,dict(effective=got,sources=sources),state='fail' if errors else 'pass' if used[sid] or name=='Table' and root.find('.//w:tbl',NS) is not None else 'not_used',details=errors))
    if heading_flags is not None:
        actual=[int(resolver.names.get(pstyle(p),'').split()[-1]) for p in root.iter(qn('w:p')) if resolver.names.get(pstyle(p),'').casefold().startswith('heading ')]
        expected=[h['level'] for h in heading_flags]
        checks.append(row('标题层级',dict(levels=expected),dict(levels=actual),state='pass' if actual==expected else 'fail',details='输出标题数量或层级与输入 AST 不符' if actual!=expected else None))
    heading_flags=heading_flags or ()
    # Effective values of text runs detect direct and character-style corruption.
    heading_index=0
    for part,tree in parts.items():
        if not (part=='word/document.xml' or re.fullmatch(r'word/(footnotes|endnotes|footer\d*|header\d*)\.xml',part)): continue
        for idx,para in enumerate(tree.iter(qn('w:p'))):
            text=ptext(para)
            name=resolver.names.get(pstyle(para),pstyle(para))
            name=next((n for n in preset['styles'] if n.casefold()==name.casefold()),name)
            location=f'{part}/p{idx+1}/{name}'
            _,exception=paragraph_layout(para,name,preset)
            if exception: exceptions.append(dict(location=location,text=text,style=name,**exception))
            if not text and exception is None and para.find('.//m:oMath',NS) is None: continue
            required_para=dict(preset['styles'].get(name,{}))
            if exception: required_para['line_spacing']=exception['line_spacing']
            data=dict(location=location,text=text,style=name,part=part,runs=[],has_math=para.find('.//m:oMath',NS) is not None or para.find('.//w:footnoteReference',NS) is not None)
            note=next((a for a in para.iterancestors() if a.tag in (qn('w:footnote'),qn('w:endnote'))),None)
            if note is not None:
                kind=note.tag.split('}')[-1]
                data['note_marker']=note_numbers[kind].get(note.get(qn('w:id')))
                data['note_id']=(part,note.get(qn('w:id')))
                data['note_first']=para.find('.//w:'+kind+'Ref',NS) is not None
            all_errors=[]; unsupported=False
            try:
                pv,ps=resolver.effective(para)
                if name not in preset['styles']: unsupported=True
                else:
                    for key in PARA_FIELDS:
                        # Footer alignment is directly set for odd/even layout.
                        if name=='Page Number' and key in ('alignment','left_chars') and preset['page_numbers']['kind']=='odd_even': continue
                        if not same(key,required_para[key],pv.get(key)): all_errors.append(f'{key}: {pv.get(key)} != {required_para[key]}')
                for run in para.iter(qn('w:r')):
                    txt=''.join(n.text or '' for n in run.iter(qn('w:t')))
                    if not txt: continue
                    required=expected_for_run(resolver,para,run,preset)
                    got,sources=resolver.effective(para,run)
                    data['runs'].append(dict(text=txt,required=required,effective=got,sources=sources))
                    if required is None: unsupported=True; continue
                    for key in RUN_FIELDS:
                        if not same(key,required[key],got.get(key)): all_errors.append(f'run {txt[:25]} / {key}: {got.get(key)} != {required[key]}')
                if name.startswith('Heading '):
                    level=int(name.split()[-1]); kind=preset['numbering']['kind']
                    disabled=heading_index<len(heading_flags) and heading_flags[heading_index]['disabled']
                    lvl=resolver.number_level(para)
                    if level<=preset['numbering']['levels'] and not disabled and lvl is None: all_errors.append('缺少标题编号')
                    if (disabled or kind=='none') and lvl is not None: all_errors.append('不应有自动标题编号')
                    if lvl is not None and level<=preset['numbering']['levels']:
                        nr=properties(lvl.find('w:rPr',NS))
                        for key in RUN_FIELDS:
                            if not same(key,preset['styles'][name][key],nr.get(key)): all_errors.append(f'编号 {key} 不符')
                        fmt=lvl.find('w:numFmt',NS)
                        want_fmt='chineseCounting' if kind=='gongwen' and level<=2 else 'decimal'
                        if fmt is None or fmt.get(qn('w:val'))!=want_fmt: all_errors.append('编号 numFmt 不符')
                        want=('%1','%1.%2','%1.%2.%3')[level-1] if kind=='academic' else ('%1、','（%2）','%3.','（%4）')[level-1]
                        n=lvl.find('w:lvlText',NS); suff=lvl.find('w:suff',NS)
                        if n is None or n.get(qn('w:val'))!=want or suff is None or suff.get(qn('w:val'))!=('space' if kind=='academic' else 'nothing'): all_errors.append('编号定义不符')
                    heading_index+=1
            except (ValueError,KeyError) as e: unsupported=True; all_errors.append(str(e))
            checks.append(row(location,required_para or '未支持的自定义样式',dict(runs=data['runs'],effective=pv if 'pv' in locals() else None,sources=ps if 'ps' in locals() else None),state='fail' if all_errors and not unsupported else 'unknown' if unsupported else 'pass',details=all_errors))
            paragraphs.append(data)
    for idx,table in enumerate(root.iter(qn('w:tbl'))):
        kind=preset['table']['kind']; borders=table.find('w:tblPr/w:tblBorders',NS)
        want_edges=('top','left','bottom','right','insideH','insideV') if kind=='grid' else ('top','bottom')
        actual={n.tag.split('}')[-1]:(n.get(qn('w:val')),n.get(qn('w:sz')),n.get(qn('w:color'))) for n in borders} if borders is not None else {}
        expected={k:('single','4' if kind=='grid' else '12','000000') for k in want_edges}
        errors=[]
        if actual!=expected: errors.append('tblBorders 不符')
        rows,heads=table_headers(table)
        for ridx,tr in enumerate(rows):
            for tc in tr.findall('w:tc',NS):
                edges=tc.find('w:tcPr/w:tcBorders',NS)
                e={n.tag.split('}')[-1]:(n.get(qn('w:val')),n.get(qn('w:sz')),n.get(qn('w:color'))) for n in edges} if edges is not None else {}
                expected_cell={'bottom':('single','6','000000')} if kind=='three_line' and len(rows)>1 and heads and ridx==heads-1 else {}
                if e!=expected_cell: errors.append('tcBorders 不符')
        checks.append(row(f'表格/{idx+1}',dict(kind=kind,borders=expected),dict(borders=actual),state='fail' if errors else 'pass',details=errors))
    page=preset['page']; width,height=PAPER_MM[page['paper_size']]
    if page['orientation']=='landscape': width,height=height,width
    sections=root.findall('.//w:sectPr',NS)
    for idx,section in enumerate(sections):
        size=section.find('w:pgSz',NS); margins=section.find('w:pgMar',NS)
        got=[float(size.get(qn('w:'+a)))/20 for a in ('w','h')] if size is not None else []
        want=[width*72/25.4,height*72/25.4]
        ok=len(got)==2 and all(abs(a-b)<1 for a,b in zip(got,want))
        if size is not None and size.get(qn('w:orient'),'portrait')!=page['orientation']: ok=False
        grid=section.find('w:docGrid',NS)
        if page['grid_line_pitch'] and (grid is None or grid.get(qn('w:linePitch'))!=str(page['grid_line_pitch'])): ok=False
        if margins is None: ok=False
        else:
            for a,v in zip(('top','bottom','left','right'),page['margins_cm']):
                if abs(float(margins.get(qn('w:'+a)))/20-v*72/2.54)>1: ok=False
        checks.append(row(f'页面/{idx+1}',page,dict(size_pt=got),state='pass' if ok else 'fail'))
    if not sections: checks.append(row('页面',page,state='fail',details='无 sectPr'))
    footer_parts=[tree for name,tree in parts.items() if re.fullmatch(r'word/footer\d*\.xml',name)]
    page_fields=[n for tree in footer_parts for n in tree.iter() if n.tag==qn('w:fldSimple') and 'PAGE' in n.get(qn('w:instr'),'') or n.tag==qn('w:instrText') and 'PAGE' in (n.text or '')]
    checks.append(row('页脚/PAGE','页脚有动态 PAGE 域',state='pass' if page_fields else 'fail'))
    return dict(status=status(checks),checks=checks,paragraphs=paragraphs,line_spacing_exceptions=exceptions,repeated_table_headers=[''.join(ptext(p) for row in table_headers(t)[0][:table_headers(t)[1]] for p in row.iter(qn('w:p'))) for t in root.iter(qn('w:tbl')) if table_headers(t)[1]])


def black(color):
    if color is None: return True  # PDF default fill is device black.
    if isinstance(color,(int,float)): return abs(color)<1e-5
    if isinstance(color,(tuple,list)):
        if len(color)==4: return all(abs(c)<1e-5 for c in color[:3]) and abs(color[3]-1)<1e-5
        return all(abs(c)<1e-5 for c in color)
    return False


def font_key(font):
    font=re.sub(r'^[A-Z]{6}\+','',str(font))
    return re.sub('[^a-z0-9]','',font.casefold())


def font_matches(actual,required):
    a=font_key(actual); b=font_key(required)
    aliases={'songtisc':['stsongtisc'],'heitisc':['stheitisc'],'kaitisc':['stkaitisc'],'timesnewroman':['timesnewromanps'],'couriernew':['couriernewps'],'fangsong':['stfangsong'],'notoserifcjksc':['notoserifcjksc'],'notosanscjksc':['notosanscjksc']}
    for stem in [b]+aliases.get(b,[]):
        if a==stem or a.startswith(stem) and re.fullmatch(r'(regular|roman|bold|italic|bolditalic|psmt|psboldmt|psitalicmt|psbolditalicmt|mt|medium|light|semibold|ps|psregular|psregularmt)*',a[len(stem):]): return True
    return False


def allowed_fonts(required,decisions):
    return list(next((d['allowed'] for d in decisions if d['actual']==required or d['required']==required),[required]))


def text_segments(para_data):
    # Math carries separate OMML text; verify surrounding editable text separately.
    if para_data['has_math']: return [r['text'] for r in para_data['runs'] if norm(r['text'])]
    return [para_data['text']]


def check_pdf(path,preset,docx_result,decisions,strict=False):
    checks=[]; warnings=[]; allchars=[]; sizes=[]
    try:
        with pdfplumber.open(path) as pdf:
            if not pdf.pages: return dict(status='fail',checks=[row('PDF','至少一页',state='fail')],warnings=[],pages=0)
            for idx,page in enumerate(pdf.pages):
                sizes.append([page.width,page.height]); allchars.extend(dict(c,_page=idx,_height=page.height) for c in page.chars)
                errors=[]
                for c in page.chars:
                    if not black(c.get('non_stroking_color')): errors.append(f'非黑文字: {c["text"]}')
                    if c['x0']<-1 or c['x1']>page.width+1 or c['top']<-1 or c['bottom']>page.height+1: errors.append(f'文字出界: {c["text"]}')
                w,h=PAPER_MM[preset['page']['paper_size']]
                if preset['page']['orientation']=='landscape': w,h=h,w
                if abs(page.width-w*72/25.4)>2 or abs(page.height-h*72/25.4)>2: errors.append('页面尺寸不符')
                checks.append(row(f'PDF/页面{idx+1}',dict(page=preset['page'],color='black',coordinates='inside page'),pdf=dict(size_pt=sizes[-1]),state='fail' if errors else 'pass',details=errors))
    except Exception as e: return dict(status='fail',checks=[row('PDF','可读取',state='fail',details=str(e))],warnings=[],pages=0)
    # The PDF drawing stream interleaves footers, repeated table headers and
    # footnotes with body paragraphs. Remove only identified generated furniture;
    # never use fuzzy matching or arbitrary skipped text to conceal lost content.
    body_bottom_cm=preset['page']['margins_cm'][1]
    body_top_pt=preset['page']['margins_cm'][0]*72/2.54
    bodychars=[c for c in allchars if c['top'] < c['_height']-body_bottom_cm*72/2.54+1]
    footerchars=[c for c in allchars if c['top'] >= c['_height']-body_bottom_cm*72/2.54+1]
    page_style=preset['styles']['Page Number']
    for page_idx in range(len(sizes)):
        glyphs=[c for c in footerchars if c['_page']==page_idx and norm(c['text'])]
        text=''.join(c['text'] for c in glyphs)
        want=f'— {page_idx+1} —' if preset['page_numbers']['kind']=='odd_even' else str(page_idx+1)
        errors=[]
        if norm(text)!=norm(want): errors.append('页码文字或 PAGE 域结果不符')
        for c in glyphs:
            if abs(c['size']-page_style['size'])>0.65: errors.append('页码字号不符')
            if not font_matches(c['fontname'],page_style['ascii']):
                message=f'页码字体替换 {page_style["ascii"]} → {c["fontname"]}'
                if strict: errors.append(message)
                elif message not in warnings: warnings.append(message)
        checks.append(row(f'PDF/页码{page_idx+1}',dict(text=want,style=page_style),pdf=dict(text=text,fonts=sorted({c['fontname'] for c in glyphs}),sizes=sorted({round(c['size'],2) for c in glyphs})),state='fail' if errors else 'pass',details=errors))
    footnote_chars=[]; removed_ids=set(); ambiguous_notes=set(); ambiguous_glyphs=set(); anchors={}
    raw=''.join(norm(c['text']) for c in bodychars)
    rawchars=[c for c in bodychars for letter in c['text'] if not letter.isspace()]
    for para in docx_result['paragraphs']:
        if para['part'] not in ('word/footnotes.xml','word/endnotes.xml'): continue
        target=norm(para['text']); start=0; candidates=[]
        while target:
            pos=raw.find(target,start)
            if pos<0: break
            span=rawchars[pos:pos+len(target)]; start=pos+1
            if not span or any(id(c) in removed_ids for c in span): continue
            first=span[0]; page=first['_page']; top=first['top']
            # A generated note marker sits at the left edge of the first note
            # line, before its text. Do not use expected font/size to select the
            # candidate: those are the values this check must independently test.
            left=preset['page']['margins_cm'][2]*72/2.54
            marker=[c for c in bodychars if c['_page']==page and c['x1']<=first['x0']+0.5 and c['x0']>=left-2 and c['x0']<=left+12 and first['x0']-c['x1']<30 and abs(c['top']-top)<5 and c['size']<first['size']*0.85 and norm(c['text'])]
            marker.sort(key=lambda c:c['x0'])
            marked=bool(para.get('note_marker') and max(c['bottom'] for c in span)>first['_height']/2 and ''.join(c['text'] for c in marker)==para['note_marker'])
            anchor=anchors.get(para.get('note_id'))
            continued=bool(anchor and not para.get('note_first') and page==anchor['_page'] and top>=anchor['bottom']-1 and top-anchor['bottom']<40)
            candidates.append((span,marker if marked else [],marked or continued))
        certain=[c for c in candidates if c[2]]
        body_overlap=any(target and target in norm(p['text']) for p in docx_result['paragraphs'] if p['part']=='word/document.xml')
        chosen=certain[0] if len(certain)==1 else candidates[0] if len(candidates)==1 and not body_overlap else None
        if chosen is None:
            if candidates:
                ambiguous_notes.add(para['location'])
                ambiguous_glyphs.update(id(c) for span,_,_ in candidates for c in span)
            continue
        span,marker,_=chosen
        footnote_chars.extend(span); removed_ids.update(id(c) for c in span+marker)
        if para.get('note_id'): anchors[para['note_id']]=max(span,key=lambda c:c['bottom'])
    bodychars=[c for c in bodychars if id(c) not in removed_ids]
    # Remove only repetitions of declared headers located at the top of a page.
    chars=[c for c in bodychars for letter in c['text'] if not letter.isspace()]
    stream=''.join(letter for c in bodychars for letter in c['text'] if not letter.isspace())
    repeated=set()
    for header in set(docx_result.get('repeated_table_headers',[])):
        target=norm(header); pos=0; first=True
        while target:
            hit=stream.find(target,pos)
            if hit<0: break
            span=chars[hit:hit+len(target)]
            if not first and span and span[0]['top']<=body_top_pt+40:
                repeated.update(range(hit,hit+len(target)))
            first=False; pos=hit+len(target)
    kept=[(i,c) for i,c in enumerate(chars) if i not in repeated]
    stream=''.join(stream[i] for i,c in kept)
    chars=[dict(c,text=stream[k],_ambiguous=id(c) in ambiguous_glyphs) for k,(i,c) in enumerate(kept)]
    notes_chars=[c for c in footnote_chars for letter in c['text'] if not letter.isspace()]
    notes_stream=''.join(letter for c in footnote_chars for letter in c['text'] if not letter.isspace())
    claimed=set(); notes_claimed=set()
    cjk_allowed={font for s in preset['styles'].values() for font in allowed_fonts(s['eastAsia'],decisions)}
    bad=[dict(text=c['text'],font=c['fontname']) for c in allchars if any(is_cjk(x) for x in c['text']) and not any(font_matches(c['fontname'],f) for f in cjk_allowed)]
    checks.append(row('PDF/中文缺字风险','中文使用要求字体或回退字体',pdf=dict(unexpected=bad),state='fail' if bad else 'pass',details='检查 LibreOffice fontconfig 环境' if bad else None))
    for para in docx_result['paragraphs']:
        if re.match(r'word/(footer|header)',para['part']): continue  # PAGE is evaluated per page.
        if para['location'] in ambiguous_notes:
            checks.append(row(para['location']+'/内容','区分正文与脚注的同文候选',state='unknown',details='无法从位置和脚注标记确定文本归属'))
            checks.append(row(para['location']+'/格式',preset['styles'].get(para['style']),state='unknown',details='文本归属不确定，未推断字体或字号'))
            continue
        selected=[]; missing=[]
        if para['part'] in ('word/footnotes.xml','word/endnotes.xml'):
            active_stream,active_chars,active_claimed=notes_stream,notes_chars,notes_claimed
        else:
            active_stream,active_chars,active_claimed=stream,chars,claimed
        for segment in text_segments(para):
            target=norm(segment)
            if not target: continue
            start=0; found=None
            while True:
                pos=active_stream.find(target,start)
                if pos<0: break
                inds=range(pos,pos+len(target))
                if not any(i in active_claimed for i in inds): found=pos; break
                start=pos+1
            if found is None: missing.append(segment)
            else:
                inds=range(found,found+len(target)); active_claimed.update(inds); selected.extend(active_chars[i] for i in inds)
        checks.append(row(para['location']+'/内容','DOCX 文字在 PDF 中保留（重复文字逐次匹配）',pdf=dict(text=para['text'],missing=missing),state='fail' if missing else 'pass'))
        if missing:
            checks.append(row(para['location']+'/格式',preset['styles'].get(para['style']),pdf=None,state='unknown',details='无法匹配段落')); continue
        if any(c.get('_ambiguous') for c in selected):
            checks.append(row(para['location']+'/格式',preset['styles'].get(para['style']),state='unknown',details='正文与脚注同文候选无法区分，未推断字体或字号'))
            continue
        errors=[]; unknown=False; run_pos=0; observed=[]
        for run in para['runs']:
            required=run['required']; target=norm(run['text'])
            got=selected[run_pos:run_pos+len(target)]; run_pos+=len(target)
            if not target: continue
            if required is None: unknown=True; continue
            records=Counter((c['fontname'],round(c['size'],2),str(c.get('non_stroking_color'))) for c in got)
            observed.append(dict(text=run['text'],glyphs=[dict(font=f,size=size,color=color,count=count) for (f,size,color),count in records.items()]))
            for c in got:
                chinese=any(is_cjk(x) for x in c['text'])
                east=chinese or bool(re.search(r'[\u3000-\u303f\uff00-\uffef]',c['text']))
                font=required['eastAsia'] if east else required['ascii']
                # Punctuation and mathematical symbols may use the East Asian font.
                candidates=allowed_fonts(font,decisions)
                if not chinese: candidates+=allowed_fonts(required['eastAsia'],decisions)
                if not any(font_matches(c['fontname'],f) for f in candidates):
                    message=f'{para["location"]}: 字体替换 {font} → {c["fontname"]}'
                    if chinese or strict: errors.append(message)
                    elif message not in warnings: warnings.append(message)
                elif not font_matches(c['fontname'],font):
                    message=f'{para["location"]}: 字体替换 {font} → {c["fontname"]}'
                    if strict: errors.append(message)
                    elif message not in warnings: warnings.append(message)
                if abs(c['size']-required['size'])>0.65: errors.append(f'字号 {c["size"]:.2f} != {required["size"]}')
                if not black(c.get('non_stroking_color')): errors.append('非黑文字')
        checks.append(row(para['location']+'/格式',preset['styles'].get(para['style']),docx=dict(runs=para['runs']),pdf=dict(runs=observed),state='fail' if errors else 'unknown' if unknown else 'pass',details=sorted(set(errors))))
    return dict(status=status(checks),checks=checks,warnings=warnings,pages=len(sizes),page_sizes_pt=sizes)
