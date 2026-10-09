import pathlib,re,runpy,sys
code=pathlib.Path(__file__).resolve().parents[1]/'local-break-constraints-v1/code';sys.path.insert(0,str(code));import atoms
atoms.MATH=re.compile(r'(?!)');runpy.run_path(str(code/'run_page.py'),run_name='__main__')
