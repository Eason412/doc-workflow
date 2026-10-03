#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["python-docx", "pdfplumber"]
# ///
"""Markdown → reference-based DOCX → LibreOffice PDF, verified before publication."""
from __future__ import annotations
import argparse
import json
import math
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import sys
import tempfile

from presets import ConfigError, load_preset, font_environment, installed_fonts, resolve_fonts, PAPER_MM
from ooxml import build_reference, postprocess
from checks import check_docx, check_pdf, row

NOT_CHECKED=['图片、公式的视觉呈现与宽表、大图需要渲染页面目视检查','图片内部文字颜色不在可编辑文字的黑色检查范围内','固定行距段落的行内图片仍可能被裁切；含 OMML 的固定行距段落使用同值最小行距','visual 始终为 not_done，自动检查不能替代目视验收']

class ConversionError(Exception):
    def __init__(self,message,code=1,report=None):
        super().__init__(message); self.code=code; self.report=report


class PublicationError(OSError):
    def __init__(self,error,recovery):
        self.publication_error=str(error); self.recovery=recovery
        failed=[r for r in recovery if r['status']=='fail']
        super().__init__(str(error)+('；回滚失败，详见恢复记录' if failed else ''))


def run(cmd,timeout,env=None):
    try:
        proc=subprocess.Popen([str(x) for x in cmd],stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,encoding='utf-8',errors='replace',start_new_session=os.name=='posix',env=env)
    except OSError as e: raise ConversionError(f'无法运行 {cmd[0]}: {e}') from e
    try: stdout,stderr=proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        if os.name=='posix':
            try: os.killpg(proc.pid,signal.SIGKILL)
            except ProcessLookupError: pass
        else: subprocess.run(['taskkill','/F','/T','/PID',str(proc.pid)],capture_output=True)
        proc.communicate()
        raise ConversionError(f'{Path(cmd[0]).name} 超时 ({timeout:g}s)') from None
    if proc.returncode: raise ConversionError(f'{Path(cmd[0]).name} 退出码 {proc.returncode}: {stderr.strip()}')
    return subprocess.CompletedProcess(cmd,proc.returncode,stdout,stderr)


def find_soffice(explicit=None,required=True):
    candidate=explicit or os.environ.get('MD_EXPORT_SOFFICE') or shutil.which('soffice')
    if candidate:
        candidate=os.path.expanduser(candidate)
        found=shutil.which(candidate)
        if found: return str(Path(found).absolute())  # Preserve the fontconfig wrapper, not its target.
    if required: raise ConversionError('找不到 soffice；使用 --soffice 或 MD_EXPORT_SOFFICE',2)
    return None


def ast_text(node):
    if isinstance(node,list): return ''.join(ast_text(n) for n in node)
    if not isinstance(node,dict): return ''
    kind=node.get('t'); content=node.get('c')
    if kind=='Str': return content
    if kind in ('Space','SoftBreak','LineBreak'): return ' '
    if kind in ('Code','Math'): return content[1]
    return ast_text(content)


def headers(node):
    if isinstance(node,list):
        for n in node: yield from headers(n)
    elif isinstance(node,dict):
        if node.get('t')=='Header': yield node
        else: yield from headers(node.get('c'))


def handwritten(text,level,kind):
    text=text.strip()
    if kind=='academic':
        patterns={1:r'^\d+[.、]?\s+\S',2:r'^\d+\.\d+(?:\s+|[、.]\s*)\S',3:r'^\d+\.\d+\.\d+(?:\s+|[、.]\s*)\S'}
        # A year followed by 年 is ordinary text, even when a space follows the digits.
        if re.match(r'^\d{4}\s*年',text): return False
    elif kind=='gongwen':
        patterns={1:r'^[一二三四五六七八九十百零〇]+、\s*\S',2:r'^（[一二三四五六七八九十百零〇]+）\s*\S',3:r'^\d+\.(?!\d)\s*\S',4:r'^（\d+）\s*\S'}
    else: return False
    return bool(re.match(patterns.get(level,r'(?!)'),text))


def unsupported_ast(node):
    if isinstance(node,list): return any(unsupported_ast(n) for n in node)
    if isinstance(node,dict):
        if node.get('t') in ('RawBlock','RawInline') and node.get('c',[None])[0] in ('openxml','docx'): return True
        return unsupported_ast(node.get('c'))
    return False


def prepare_ast(ast,preset):
    title=ast_text(ast.get('meta',{}).get('title',{})).strip()
    removed=None
    first=next((h for h in headers(ast['blocks']) if h['c'][0]==1),None)
    if title and first is not None and ast_text(first['c'][2]).strip()==title:
        def remove(node):
            if isinstance(node,list):
                for n in list(node):
                    if n is first: node.remove(n); return True
                    if remove(n): return True
            elif isinstance(node,dict): return remove(node.get('c'))
            return False
        remove(ast['blocks']); removed=title
    flags=[]
    for h in headers(ast['blocks']):
        level,attr,inlines=h['c']; text=ast_text(inlines).strip()
        manual=handwritten(text,level,preset['numbering']['kind'])
        unnumbered='unnumbered' in attr[1]
        flags.append(dict(level=level,text=text,disabled=manual or unnumbered,reason='handwritten' if manual else 'unnumbered' if unnumbered else None))
    return ast,flags,removed


def targets(args,md):
    output=args.output.expanduser().absolute() if args.output else md.with_suffix('.docx')
    ext=output.suffix.casefold()
    if ext not in ('.docx','.pdf'): raise ConversionError('--output 扩展名必须是 .docx 或 .pdf',2)
    to=args.to or ('pdf' if ext=='.pdf' else 'docx')
    if args.to in ('docx','pdf') and args.output is not None and ext!='.'+args.to: raise ConversionError('--to 与 --output 扩展名冲突',2)
    outputs=[output.with_suffix('.'+kind) for kind in ['docx','pdf']] if to=='both' else [output if args.output is not None else output.with_suffix('.'+to)]
    if any(p.resolve()==md.resolve() for p in outputs): raise ConversionError('输入与输出不能同路径',2)
    return to,outputs


def publish(files):
    """Stage on destination filesystems. Roll back a previously replaced first output."""
    staged=[]; backups=[]; replaced=[]; retained=set()
    try:
        for src,dest in files:
            dest.parent.mkdir(parents=True,exist_ok=True)
            fd,temp=tempfile.mkstemp(prefix='.'+dest.name+'.',suffix='.tmp',dir=dest.parent); os.close(fd)
            temp=Path(temp); staged.append((temp,dest)); shutil.copyfile(src,temp)
            backup=None
            if dest.exists():
                fd,name=tempfile.mkstemp(prefix='.'+dest.name+'.',suffix='.bak',dir=dest.parent); os.close(fd)
                backup=Path(name)
            backups.append((dest,backup))
            if backup: shutil.copy2(dest,backup)
        for temp,dest in staged:
            os.replace(temp,dest); replaced.append(dest)
    except BaseException as error:
        recovery=[]
        for dest,backup in reversed(backups):
            if dest not in replaced: continue
            record=dict(output=str(dest),backup=str(backup) if backup else None,status='pass')
            try:
                if backup is None: dest.unlink(missing_ok=True)
                else: os.replace(backup,dest)
            except OSError as restore_error:
                if backup: retained.add(backup)
                record.update(status='fail',error=str(restore_error))
            recovery.append(record)
        raise PublicationError(error,recovery) from error

    finally:
        for temp,dest in staged: temp.unlink(missing_ok=True)
        for dest,backup in backups:
            if backup and backup not in retained: backup.unlink(missing_ok=True)


def libreoffice(docx,tmp,soffice,timeout,env):
    out=tmp/'lo-output'; out.mkdir()
    profile=tmp/'lo-profile'
    proc=run([soffice,'-env:UserInstallation='+profile.as_uri(),'--headless','--convert-to','pdf','--outdir',out,docx],timeout,env)
    pdf=out/(docx.stem+'.pdf')
    if not pdf.is_file() or not pdf.stat().st_size: raise ConversionError('soffice 退出码 0 但未生成 PDF')
    return pdf,proc


def convert(args):
    md=args.input.expanduser().resolve()
    if not md.is_file(): raise ConversionError(f'输入不存在: {md}',2)
    if not math.isfinite(args.timeout) or args.timeout<=0: raise ConversionError('--timeout 必须为正数',2)
    to,outputs=targets(args,md)
    try: original=load_preset(args.preset,args.set,args.paper_size,args.orientation)
    except ConfigError as e: raise ConversionError(str(e),2) from e
    pandoc=shutil.which('pandoc')
    if not pandoc: raise ConversionError('找不到 pandoc',2)
    needs_pdf=to in ('pdf','both'); soffice=find_soffice(args.soffice,needs_pdf)
    env=font_environment(soffice)
    try: preset,decisions=resolve_fonts(original,installed_fonts(env),args.strict_fonts)
    except ConfigError as e: raise ConversionError(str(e),2) from e
    report=dict(input=str(md),outputs=[str(x) for x in outputs],preset=original['label'],font_decisions=decisions,fontconfig_file=env.get('FONTCONFIG_FILE'),soffice=soffice,conversion='unknown',docx_check='unknown',pdf_check='unknown',visual='not_done',checks=[],warnings=[],not_checked=NOT_CHECKED,published=False)
    report['warnings'] += [f'字体 {d["required"]} → {d["actual"]} ({"降级" if d["degraded"] else d["status"]})' for d in decisions if d['status']!='pass']
    with tempfile.TemporaryDirectory(prefix='md-export-') as tmp_name:
        tmp=Path(tmp_name)
        try:
            fmt='markdown' if args.no_hard_line_breaks else 'markdown+hard_line_breaks'
            proc=run([pandoc,md,'-f',fmt,'-t','json'],args.timeout)
            ast,flags,removed=prepare_ast(json.loads(proc.stdout),preset)
            report['title_deduplicated']=removed; report['numbering_disabled']=[f for f in flags if f['disabled']]
            ast_path=tmp/'input.json'; ast_path.write_text(json.dumps(ast,ensure_ascii=False),encoding='utf-8')
            default=tmp/'default.docx'; reference=tmp/'reference.docx'; docx=tmp/'document.docx'
            run([pandoc,'-o',default,'--print-default-data-file','reference.docx'],args.timeout)
            build_reference(default,reference,preset)
            proc=run([pandoc,ast_path,'-f','json','-t','docx','--reference-doc='+str(reference),'--syntax-highlighting=none','--table-caption-position=above','--figure-caption-position=below','--resource-path='+str(md.parent),'-o',docx],args.timeout)
            if proc.stderr.strip(): report['warnings'].append(proc.stderr.strip())
            if postprocess(docx,preset,flags): report['warnings'].append('Pandoc 未保留奇偶页页脚设置，公文页码退为居中')
            report['conversion']='pass'
            dx=check_docx(docx,preset,flags); report['docx_check']=dx['status']; report['checks']+=dx['checks']; report['line_spacing_exceptions']=dx['line_spacing_exceptions']
            report['conversion']='pass'
            if unsupported_ast(ast['blocks']):
                report['checks'].append(row('raw OOXML','仅支持本工具生成的结构',state='unknown'))
                report['docx_check']='unknown'
                raise ConversionError('raw OOXML 不在核对器支持范围内')
            if dx['status']!='pass': raise ConversionError('DOCX 核对未通过')
            pdf=None
            if needs_pdf:
                report['conversion']='unknown'
                pdf,proc=libreoffice(docx,tmp,soffice,args.timeout,env)
                report['conversion']='pass'
                px=check_pdf(pdf,preset,dx,decisions,args.strict_fonts)
                report['pdf_check']=px['status']; report['checks']+=px['checks']; report['warnings']+=px['warnings']
                # Attach actual PDF observations to DOCX paragraph/style rows.
                pdf_formats={c['location'].removesuffix('/格式'):c['pdf'] for c in px['checks'] if c['location'].endswith('/格式')}
                for check in dx['checks']:
                    if check['location'] in pdf_formats: check['pdf']=pdf_formats[check['location']]
                    if check['location'].startswith('样式/'):
                        name=check['location'].removeprefix('样式/')
                        observations=[pdf_formats[d['location']] for d in dx['paragraphs'] if d['style']==name and d['location'] in pdf_formats]
                        if observations: check['pdf']=observations
                report['pages']=px['pages']; report['page_sizes_pt']=px.get('page_sizes_pt')
                if px['status']!='pass': raise ConversionError('PDF 核对未通过；检查报告中的 fail/unknown')
            else: report['not_checked']=NOT_CHECKED+['仅导出 DOCX，本次 PDF 检查未执行']
            publish([(docx if dest.suffix.casefold()=='.docx' else pdf,dest) for dest in outputs])
            report['published']=True
            if preset['name']=='gongwen': report['gongwen']=dict(preset_conformance='pass',font_degraded=any(d['degraded'] or d['status']=='fallback' for d in decisions))
        except Exception as e:
            if report['conversion']=='unknown': report['conversion']='fail'
            report['error']=str(e)
            if isinstance(e,PublicationError): report['publication']=dict(status='fail',error=e.publication_error,recovery=e.recovery)
            diagnostic_parent=args.diagnostics.expanduser().absolute() if args.diagnostics else Path(tempfile.gettempdir())
            diagnostic_parent.mkdir(parents=True,exist_ok=True)
            diagnostic=Path(tempfile.mkdtemp(prefix='md-export-diagnostics-',dir=diagnostic_parent))
            # Profile files are unnecessary for diagnosis; preserve artifacts and full report.
            for file in tmp.iterdir():
                if file.name=='lo-profile': continue
                if file.is_dir(): shutil.copytree(file,diagnostic/file.name)
                else: shutil.copy2(file,diagnostic/file.name)
            report['diagnostics']=str(diagnostic)
            (diagnostic/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
            raise ConversionError(str(e),getattr(e,'code',1),report) from e
    return report


def parse_args(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('input',type=Path); p.add_argument('--output',type=Path)
    p.add_argument('--to',choices=['docx','pdf','both']); p.add_argument('--preset',default='general')
    p.add_argument('--set',action='append',default=[],metavar='KEY=VALUE')
    p.add_argument('--paper-size',type=str.upper,choices=sorted(PAPER_MM)); p.add_argument('--orientation',choices=['portrait','landscape'])
    p.add_argument('--no-hard-line-breaks',action='store_true'); p.add_argument('--strict-fonts',action='store_true')
    p.add_argument('--soffice'); p.add_argument('--timeout',type=float,default=120); p.add_argument('--diagnostics',type=Path)
    return p.parse_args(argv)


def main(argv=None):
    args=parse_args(argv)
    try: report=convert(args)
    except (ConversionError,OSError) as e:
        report=getattr(e,'report',None) or dict(error=str(e),conversion='fail',docx_check='unknown',pdf_check='unknown',visual='not_done',published=False)
        print(json.dumps(report,ensure_ascii=False,indent=2)); return getattr(e,'code',1)
    print(json.dumps(report,ensure_ascii=False,indent=2)); return 0

if __name__=='__main__': raise SystemExit(main())
