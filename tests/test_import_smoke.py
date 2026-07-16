import sys, types, importlib, pkgutil

class Any:
    def __init__(self,*a,**k): pass
    def __call__(self,*a,**k): return Any()
    def __getattr__(self,n): return _Class if n and n[0].isupper() else Any()
    def __or__(self,o): return Any()
    def __ror__(self,o): return Any()
    def __getitem__(self,i): return Any()
    def __iter__(self): return iter([])

class _MetaAny(type):
    def __getattr__(cls,n): return Any()
class _Class(metaclass=_MetaAny):
    def __init__(self,*a,**k): pass
    def __getattr__(self,n): return Any()
    @classmethod
    def new_with_range(cls,*a,**k): return _Class()
    @classmethod
    def new(cls,*a,**k): return _Class()
    @classmethod
    def new_from_icon_name(cls,*a,**k): return _Class()

class Mod(types.ModuleType):
    def __getattr__(self,n):
        return _Class if (n and n[0].isupper()) else Any()

gi = Mod("gi"); gi.require_version=lambda *a,**k:None
gi.repository = Mod("gi.repository")
sys.modules["gi"]=gi; sys.modules["gi.repository"]=gi.repository
for name in ("Gtk","Adw","Gio","GLib","Gdk","Pango","GObject"):
    m=Mod("gi.repository."+name)
    setattr(gi.repository,name,m); sys.modules["gi.repository."+name]=m

import qdvc
mods=[]
for pkg in ("qdvc.gtk3","qdvc.gtk4"):
    p=importlib.import_module(pkg)
    for mi in pkgutil.iter_modules(p.__path__, pkg+"."):
        mods.append(mi.name)
for name in mods:
    importlib.import_module(name)
    print("imported", name)
print("SMOKE IMPORT OK:", len(mods), "view modules")
