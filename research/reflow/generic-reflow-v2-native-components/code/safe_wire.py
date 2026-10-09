"""Opt-in module-local JSON facade; no mutation of the standard json module."""
import dataclasses,json as _stdlib_json,pathlib,sys
@dataclasses.dataclass(frozen=True)
class WireConfig:
    indent:None=None
    separators:tuple[str,str]=(',',':')
    retain_all_fields:bool=True
    def json(self):return dataclasses.asdict(self)
class CompactJSON:
    def __init__(self,name,config=WireConfig()):self.name=name;self.config=config;self.calls=0;self.characters=0
    def __getattr__(self,name):return getattr(_stdlib_json,name)
    def dumps(self,obj,**kwargs):
        kwargs['indent']=self.config.indent;kwargs['separators']=self.config.separators;result=_stdlib_json.dumps(obj,**kwargs);self.calls+=1;self.characters+=len(result);return result
    def dump(self,obj,fp,**kwargs):fp.write(self.dumps(obj,**kwargs))
def install(root):
    root=pathlib.Path(root).resolve();changed=[]
    for name,module in list(sys.modules.items()):
        namespace=vars(module) if isinstance(module,type(sys)) else {};filename=namespace.get('__file__')
        if not filename or not pathlib.Path(filename).is_absolute() or not pathlib.Path(filename).is_relative_to(root):continue
        if not pathlib.Path(filename).resolve().is_relative_to(root):continue
        if namespace.get('json') is _stdlib_json:
            facade=CompactJSON(name);module.json=facade;changed.append((str(pathlib.Path(filename).resolve().relative_to(root)),facade))
    return changed
def report(changed):return {'config':WireConfig().json(),'modules':[{'source':name,'dumps_calls':facade.calls,'encoded_characters':facade.characters} for name,facade in changed],'standard_json_module_modified':False,'fields_dropped':False}
