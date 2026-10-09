"""独立 AI 代理复核：所有程序运行与输出修改都发生在临时副本。"""
import ast
import datetime as dt
import itertools
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys
import tempfile
import time
from fractions import Fraction

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'reports' / 'agent-review'
ZONE = dt.timezone(dt.timedelta(hours=8))
LOG = []
RESULT = {}

def now():
    return dt.datetime.now(ZONE).isoformat(timespec='milliseconds')

def record(text):
    LOG.append(text)
    print(text, flush=True)

def run(args, cwd):
    command = [sys.executable] + list(args)
    start = time.perf_counter()
    record(f'\n[{now()}] cwd={cwd}\n$ ' + ' '.join(command))
    result = subprocess.run(command, cwd=cwd, text=True, encoding='utf-8', capture_output=True,
                            env={**os.environ, 'PYTHONDONTWRITEBYTECODE': '1'})
    record(f'exit={result.returncode}, seconds={time.perf_counter()-start:.6f}\nstdout:\n{result.stdout}stderr:\n{result.stderr}')
    return result

TOKEN = re.compile(r"\d+'\d+/\d+|\d+/\d+|\d+|[()+−×÷*/-]")

def number(token):
    if "'" in token:
        whole, part = token.split("'")
        n, d = map(int, part.split('/'))
        return Fraction(int(whole)) + Fraction(n, d)
    if '/' in token:
        n, d = map(int, token.split('/'))
        return Fraction(n, d)
    return Fraction(int(token))

def independent_tree(text):
    # 将生成的规范题面转成 Python AST；数字逐个转成精确 Fraction 调用，
    # 自己走访白名单节点；不调用项目解析器、key 或已有测试求值器。
    text = text.strip().removesuffix('=').strip()
    parts = []
    cursor = 0
    for match in TOKEN.finditer(text):
        assert not text[cursor:match.start()].strip()
        token = match.group()
        if token[0].isdigit():
            val = number(token)
            parts.append(f'F({val.numerator},{val.denominator})')
        else:
            parts.append({'−':'-', '×':'*', '÷':'/'}.get(token, token))
        cursor = match.end()
    assert not text[cursor:].strip()
    node = ast.parse(' '.join(parts), mode='eval').body
    def walk(n):
        if isinstance(n, ast.Call):
            assert isinstance(n.func, ast.Name) and n.func.id == 'F'
            assert len(n.args) == 2 and all(isinstance(a, ast.Constant) for a in n.args)
            val = Fraction(n.args[0].value, n.args[1].value)
            return ('n', val.numerator, val.denominator), val
        assert isinstance(n, ast.BinOp)
        left, lv = walk(n.left)
        right, rv = walk(n.right)
        op = {ast.Add:'+', ast.Sub:'-', ast.Mult:'*', ast.Div:'/'}[type(n.op)]
        if op == '+': value = lv + rv
        elif op == '-': value = lv - rv
        elif op == '*': value = lv * rv
        else: value = lv / rv
        return (op, left, right), value
    return walk(node)

def orbit(tree):
    if tree[0] == 'n': return {tree}
    op, left, right = tree
    variants = {(op,a,b) for a,b in itertools.product(orbit(left), orbit(right))}
    if op in ('+', '*'):
        variants |= {(op,b,a) for _,a,b in list(variants)}
    return variants

def tree_of_expr(e):
    if not e.op: return ('n', e.value.numerator, e.value.denominator)
    return (e.op, tree_of_expr(e.left), tree_of_expr(e.right))

def verify_output(directory, expected):
    exercise_lines = (directory/'Exercises.txt').read_text().splitlines()
    answer_lines = (directory/'Answers.txt').read_text().splitlines()
    assert len(exercise_lines) == len(answer_lines) == expected
    signatures = set()
    operators = set()
    for index,(ex,ans) in enumerate(zip(exercise_lines,answer_lines),1):
        prefix=f'{index}. '
        assert ex.startswith(prefix) and ans.startswith(prefix)
        tree,value = independent_tree(ex[len(prefix):])
        assert number(ans[len(prefix):]) == value, index
        signature=min(map(repr,orbit(tree)))
        assert signature not in signatures, index
        signatures.add(signature)
        def walk(t):
            if t[0] == 'n':
                val=Fraction(t[1],t[2]); assert 0<=val<10 and t[2]<10
                return val,0
            op,l,r=t; lv,lc=walk(l); rv,rc=walk(r); operators.add(op)
            if op=='+': v=lv+rv
            elif op=='-': v=lv-rv; assert v>=0
            elif op=='*': v=lv*rv
            else: v=lv/rv; assert 0<v<1
            return v,lc+rc+1
        _,count=walk(tree); assert 1<=count<=3
    record(f'Independent AST audit: {expected} lines; exact answers, operand/subexpression rules, operator counts and swap-orbit uniqueness PASS; operators={sorted(operators)}')

record(f'SCRIPT START {now()}\nPython={sys.version}\nPlatform={platform.platform()}\nSource={ROOT}')
RESULT['script_start']=now()
try:
    calculations = {'3': Fraction(17,2)*Fraction(41,5), '4': Fraction(1,2)*6, '6': Fraction(3,4)-Fraction(3,4)}
    expected_answers = {'3':"69'7/10",'4':'3','6':'0'}
    actual_lines=(ROOT/'examples'/'Answers.txt').read_text().splitlines()
    for index,value in calculations.items():
        actual=actual_lines[int(index)-1].split('. ',1)[1]
        assert value==number(actual) and actual==expected_answers[index]
        record(f'Example {index}: independent={value}; file={actual}; PASS')
    with tempfile.TemporaryDirectory(prefix='schoolwork-agent-review-') as temp:
        work=Path(temp)/'project'
        shutil.copytree(ROOT,work,ignore=shutil.ignore_patterns('.git','__pycache__','reports','.venv'))
        RESULT['temp_directory']=str(work)
        a=run(['Myapp.py','-n','10','-r','10','--seed','20261009','--output-dir','review10'],work)
        assert a.returncode==0
        verify_output(work/'review10',10)
        for name in ['Exercises.txt','Answers.txt']:
            shutil.copy2(work/'review10'/name,OUT/('generated10-'+name))
        for args in [['-n','10'],['-n','0','-r','10'],['-n','10','-r','0']]:
            a=run(['Myapp.py']+args,work)
            assert a.returncode==2 and 'Traceback' not in a.stderr
            assert ('必须提供 -r' if args==['-n','10'] else '大于或等于 1') in a.stderr
        a=run(['Myapp.py','-e','review10/Exercises.txt','-a','review10/Answers.txt','--output-dir','review10'],work)
        all_correct=(work/'review10/Grade.txt').read_text()
        assert a.returncode==0 and all_correct=='Correct: 10 (1, 2, 3, 4, 5, 6, 7, 8, 9, 10)\nWrong: 0 ()\n'
        (OUT/'grade-all-correct.txt').write_text(all_correct)
        lines=(work/'review10/Answers.txt').read_text().splitlines()
        lines[1]='2. 999999'; lines[4]='5. 999999'
        (work/'review10/StudentAnswers.txt').write_text('\n'.join(lines)+'\n')
        shutil.copy2(work/'review10/StudentAnswers.txt',OUT/'StudentAnswers.txt')
        a=run(['Myapp.py','-e','review10/Exercises.txt','-a','review10/StudentAnswers.txt','--output-dir','review10'],work)
        mixed=(work/'review10/Grade.txt').read_text()
        assert a.returncode==0 and mixed=='Correct: 8 (1, 3, 4, 6, 7, 8, 9, 10)\nWrong: 2 (2, 5)\n'
        (OUT/'grade-mixed.txt').write_text(mixed)
        # README 的三条主要命令逐条原样运行；只变更运行目录至临时副本。
        assert run(['Myapp.py','-n','10','-r','10'],work).returncode==0
        verify_output(work,10)
        assert run(['Myapp.py','-n','10000','-r','10','--seed','20261009'],work).returncode==0
        verify_output(work,10000)
        assert run(['Myapp.py','-e','Exercises.txt','-a','Answers.txt'],work).returncode==0
        grade=(work/'Grade.txt').read_text()
        assert grade.startswith('Correct: 10000 (1, 2, 3,') and grade.endswith('Wrong: 0 ()\n')
        record(f'README Grade.txt verified: Correct=10000, Wrong=0; file chars={len(grade)}')
        assert run(['tools/check.py'],work).returncode==0
        assert run(['tools/benchmark.py'],work).returncode==0
    sys.dont_write_bytecode=True
    sys.path.insert(0,str(ROOT))
    from quiz.model import Expr,binary,parse_expression
    pairs=[('23+45','45+23',True),('6×8','8×6',True),('3+(2+1)','1+2+3',True),('1+2+3','3+2+1',False),('1+4','2+3',False),('3-2','2-3',False),('1 ÷ 2','2 ÷ 1',False)]
    for left,right,expected in pairs:
        independent_same=bool(orbit(independent_tree(left)[0])&orbit(independent_tree(right)[0]))
        production_same=parse_expression(left).key()==parse_expression(right).key()
        assert independent_same==production_same==expected
        record(f'Dedup: {left!r} vs {right!r}: duplicate={production_same}; PASS')
    checks=0
    # 左右两侧各覆盖所有 4x4 个父子运算符组合，共 32 棵树；使用非零叶子避免除零。
    for parent,child,side in itertools.product('+-*/','+-*/',('left','right')):
        nested=binary(child,Expr(Fraction(9)),Expr(Fraction(2)))
        expr=binary(parent,nested,Expr(Fraction(4))) if side=='left' else binary(parent,Expr(Fraction(11)),nested)
        text=expr.render()
        independent,value=independent_tree(text)
        assert independent==tree_of_expr(expr) and value==expr.value
        assert parse_expression(text)==expr
        record(f'Parentheses {parent}/{child}/{side}: {text} => {value}; exact tree PASS')
        checks+=1
    RESULT['parenthesis_trees']=checks
    RESULT['result']='PASS'
except Exception:
    import traceback
    record(traceback.format_exc())
    RESULT['result']='FAIL'
finally:
    RESULT['script_end']=now()
    record(f'SCRIPT END {RESULT["script_end"]}; RESULT={RESULT["result"]}')
    (OUT/'execution.log').write_text('\n'.join(LOG)+'\n',encoding='utf-8')
    (OUT/'summary.json').write_text(json.dumps(RESULT,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
if RESULT['result']!='PASS': raise SystemExit(1)
