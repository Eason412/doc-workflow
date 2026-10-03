"""JSON presets, validated overrides and deterministic font selection (original code)."""
from __future__ import annotations
import copy
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parent.parent
SIZES = {'二号':22, '小二':18, '三号':16, '小三':15, '四号':14, '小四':12, '五号':10.5, '小五':9}
# macOS 上无界面 LibreOffice 用自带的 fontconfig，找不到系统字体，PDF 里的中文会丢；Homebrew 的 fontconfig 配置能找到
MAC_FONTCONFIG = (Path('/opt/homebrew/etc/fonts/fonts.conf'), Path('/usr/local/etc/fonts/fonts.conf'))
PAPER_MM = {'A4':(210,297), 'A3':(297,420), 'A5':(148,210), 'LETTER':(215.9,279.4)}
ALIASES = {'body':'Body Text', 'title':'Title', 'code':'Source Code', 'inline_code':'Verbatim Char', 'table_text':'Table Text', 'caption':'Caption', 'footnote':'Footnote Text', **{'heading'+str(i):'Heading '+str(i) for i in range(1,10)}}
FIELDS = {'ascii','eastAsia','size','bold','alignment','line_spacing','space_before','space_after','first_line_chars','left_chars','color','italic','keep_next','underline','shading','snap_to_grid'}

class ConfigError(ValueError):
    pass


def size_pt(value):
    if isinstance(value,str) and value in SIZES:
        return SIZES[value]
    try:
        result=float(re.sub(r'\s*pt$', '', str(value), flags=re.I))
    except ValueError:
        raise ConfigError(f'非法字号: {value}') from None
    if not math.isfinite(result) or not 0 < result <= 200 or result*2 != int(result*2):
        raise ConfigError(f'字号必须为 0–200 pt 内的半磅数值: {value}')
    return result


def spacing(value):
    try:
        kind,number=str(value).split(':')
        number=float(number)
        if kind not in ('fixed','multiple') or not math.isfinite(number) or number<=0:
            raise ValueError()
        return kind,number
    except ValueError:
        raise ConfigError(f'非法行距 {value}; 使用 fixed:22 或 multiple:1.5') from None


def keys(preset):
    return sorted([f'{alias}.{field}' for alias in ALIASES for field in FIELDS] + ['page.paper_size','page.orientation','page.margins_cm','table.kind'])


def validate(p):
    baseline=json.loads((ROOT/'presets/general.json').read_text())
    if not isinstance(p,dict): raise ConfigError('范式必须为 JSON 对象')
    for key in baseline:
        if key not in p:
            raise ConfigError(f'范式缺字段: {key}')
    for key in ('page','styles','table','numbering','page_numbers','font_fallbacks'):
        if not isinstance(p[key],dict): raise ConfigError(f'{key} 必须为 JSON 对象')
    for key in ('page','table','numbering','page_numbers'):
        if not baseline[key].keys() <= p[key].keys(): raise ConfigError(f'{key} 缺少必需字段')
    if any(not isinstance(p[k],str) or not p[k] for k in ('name','label')): raise ConfigError('name/label 必须为非空字符串')
    for name in baseline['styles']:
        if name not in p['styles'] or not isinstance(p['styles'][name],dict) or set(p['styles'][name]) != FIELDS:
            raise ConfigError(f'样式 {name} 必须明确指定全部字段: {sorted(FIELDS)}')
    for name,s in p['styles'].items():
        if not isinstance(s,dict) or set(s)!=FIELDS:
            raise ConfigError(f'样式 {name} 字段不完整或有未知字段')
        s['size']=size_pt(s['size'])
        spacing(s['line_spacing'])
        for f in ('bold','italic','keep_next','underline','snap_to_grid'):
            if type(s[f]) is not bool:
                raise ConfigError(f'{name}.{f} 必须为布尔值')
        if s['alignment'] not in ('left','right','center','justify'):
            raise ConfigError(f'{name}.alignment 非法')
        for f in ('space_before','space_after','first_line_chars','left_chars'):
            if type(s[f]) not in (int,float) or not math.isfinite(s[f]) or s[f]<0:
                raise ConfigError(f'{name}.{f} 必须为非负数')
        if s['color']!='000000' or s['italic']:
            raise ConfigError('范式样式要求黑色、无斜体')
        for f in ('ascii','eastAsia'):
            if not isinstance(s[f],str) or not s[f].strip():
                raise ConfigError(f'{name}.{f} 必须为字体族名')
        if s['shading'] is not None and not re.fullmatch('[0-9A-Fa-f]{6}',s['shading']):
            raise ConfigError(f'{name}.shading 必须为六位十六进制颜色或 null')
    page=p['page']
    if page['paper_size'] not in PAPER_MM or page['orientation'] not in ('portrait','landscape'):
        raise ConfigError('非法页面设置')
    if not isinstance(page['margins_cm'],list) or len(page['margins_cm'])!=4 or any(type(v) not in (int,float) or not math.isfinite(v) or v<0 for v in page['margins_cm']):
        raise ConfigError('页边距按上、下、左、右给四个非负数')
    w,h=PAPER_MM[page['paper_size']]
    if page['orientation']=='landscape': w,h=h,w
    t,b,l,r=page['margins_cm']
    if (t+b)*10>=h or (l+r)*10>=w:
        raise ConfigError('页边距必须留出正的版心')
    if p['table']['kind'] not in ('grid','three_line') or p['numbering']['kind'] not in ('none','academic','gongwen'):
        raise ConfigError('非法表格或编号类型')
    if p['numbering']['levels'] != {'none':0,'academic':3,'gongwen':4}[p['numbering']['kind']]:
        raise ConfigError('编号层数与编号类型冲突')
    if p['page_numbers']['format'] != ('— PAGE —' if p['page_numbers']['kind']=='odd_even' else 'PAGE'):
        raise ConfigError('页码 format 与 kind 冲突')
    if not isinstance(page['grid_line_pitch'],int) or page['grid_line_pitch']<0:
        raise ConfigError('grid_line_pitch 必须为非负整数')
    if type(p['page_numbers']['distance_from_body_cm']) not in (int,float) or not math.isfinite(p['page_numbers']['distance_from_body_cm']) or p['page_numbers']['distance_from_body_cm']<0:
        raise ConfigError('页码距离必须为非负数')
    if p['page_numbers']['kind'] not in ('center','odd_even'):
        raise ConfigError('非法页脚类型')
    for font,chain in p['font_fallbacks'].items():
        if not isinstance(font,str) or not isinstance(chain,list) or any(not isinstance(x,str) or not x for x in chain):
            raise ConfigError('字体回退列表非法')
    return p


def load_preset(name='general', overrides=(), paper_size=None, orientation=None):
    path=ROOT/'presets'/f'{name}.json' if name in ('general','academic','gongwen') else Path(name).expanduser()
    try:
        p=json.loads(path.read_text(encoding='utf-8'))
    except (OSError,ValueError) as e:
        raise ConfigError(f'无法读取范式 {path}: {e}') from e
    validate(p)
    for item in overrides:
        try:
            key,value=item.split('=',1)
            part,field=key.split('.',1)
            if part in ALIASES and field in FIELDS:
                target=p['styles'][ALIASES[part]]
            elif key in ('page.paper_size','page.orientation','page.margins_cm','table.kind'):
                target=p[part]
            else:
                raise ValueError()
            if field in ('bold','italic','keep_next','underline','snap_to_grid'):
                if value not in ('true','false'): raise ValueError()
                value=value=='true'
            elif field in ('space_before','space_after','first_line_chars','left_chars'): value=float(value)
            elif field=='margins_cm': value=json.loads(value)
            elif field=='shading' and value=='null': value=None
            target[field]=value
            if part=='body':
                for s in ('First Paragraph','Abstract'): p['styles'][s][field]=value
                if field=='size': p['styles']['Verbatim Char'][field]=value
        except (ValueError,KeyError) as e:
            raise ConfigError(f'非法覆盖 {item}; 可用键: {", ".join(keys(p))}') from e
    if paper_size: p['page']['paper_size']=paper_size
    if orientation: p['page']['orientation']=orientation
    try: return validate(p)
    except ConfigError as e:
        raise ConfigError(f'{e}; 可用键: {", ".join(keys(p))}') from e


def font_environment(soffice=None):
    """Use the wrapper's documented FONTCONFIG_FILE without executing arbitrary code."""
    env=os.environ.copy()
    if 'FONTCONFIG_FILE' not in env and soffice:
        try:
            script=Path(soffice).read_text()
            match=re.search(r'FONTCONFIG_FILE:=([^}\n]+)',script)
            if match:
                path=Path(os.path.expandvars(match[1].strip('"\''))).expanduser()
                if path.is_file(): env['FONTCONFIG_FILE']=str(path)
        except (OSError,UnicodeError): pass
    if 'FONTCONFIG_FILE' not in env and sys.platform=='darwin':
        found=next((p for p in MAC_FONTCONFIG if p.is_file()),None)
        if found: env['FONTCONFIG_FILE']=str(found)
    return env


def installed_fonts(env):
    tool=shutil.which('fc-list')
    if not tool: return None
    try:
        result=subprocess.run([tool,'--format','%{family}\n'],env=env,capture_output=True,text=True,timeout=20)
        if result.returncode: return None
        return {f.strip().casefold() for line in result.stdout.splitlines() for f in line.split(',')}
    except (OSError,subprocess.TimeoutExpired): return None


def resolve_fonts(preset, available, strict=False):
    p=copy.deepcopy(preset)
    if available is None and strict: raise ConfigError('--strict-fonts: fc-list 不可用，无法核验字体')
    available={s.casefold() for s in available} if available is not None else None
    decisions=[]
    for font in sorted({s[f] for s in p['styles'].values() for f in ('ascii','eastAsia')}):
        chain=[font]+p['font_fallbacks'].get(font,[])
        selected=font if available is None else next((x for x in chain if x.casefold() in available),None)
        if strict and selected!=font: raise ConfigError(f'--strict-fonts: 缺少字体 {font}')
        status='unknown' if available is None else 'missing' if selected is None else 'fallback' if selected!=font else 'pass'
        selected=selected or font
        degraded=font=='FZXiaoBiaoSong-B05S' and selected!=font
        decisions.append(dict(required=font,actual=selected,status=status,degraded=degraded,allowed=chain))
        for s in p['styles'].values():
            for f in ('ascii','eastAsia'):
                if s[f]==font:
                    s[f]=selected
                    if degraded: s['bold']=True
    return p,decisions
