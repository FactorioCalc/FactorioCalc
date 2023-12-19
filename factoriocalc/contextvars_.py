import os as _os
import sys as _sys
from warnings import warn

_useHack = False
def _check_env():
    global _useHack
    str = _os.environ['FACTORIOCALC_CONTEXTVARS_HACK']
    str = str.strip().lower()
    if str in ['y', 'yes', 't', 'true', '1']:
        _useHack = True
    elif str in ['n', 'no', 'f', 'false', '0']:
        _useHack = False
    else:
        raise ValueError('FACTORIOCALC_CONTEXTVARS_HACK')

def _check_otherwise():
    global _useHack
    try:
        if get_ipython().__class__.__module__.split('.')[0] == 'pyodide_kernel':
            _sys.stderr.write(f'notice: pyodide kernel detected, enabling contextvars hack\n')
            _useHack = True
            return
    except:
        pass
    try:
        import ipykernel
        if (isinstance(get_ipython().kernel, ipykernel.ipkernel.IPythonKernel)
            and ipykernel.version_info[0] == 5):
            _sys.stderr.write(f'notice: ipykernel version 5 detected, enabling contextvars hack\n')
            _useHack = True
            return
    except:
        pass

try:
    _check_env()
except KeyError:
    _check_otherwise()

if _useHack:
    import contextvars as _cv

    _MISSING = object()

    _is_global = _cv.ContextVar('_is_global', default = True)

    class ContextVar:
        __slots__ = ('name', '_var', '_default', '_global_val')
        def __init__(self, name, *, default = _MISSING):
            self.name = name
            self._default = default
            self._global_val = _MISSING 
            if default is _MISSING:
                self._var = _cv.ContextVar(name)
            else:
                self._var = _cv.ContextVar(name, default = default)
                
        def get(self, default = _MISSING):
            val = _MISSING
            if not _is_global.get():
                val = self._var.get(_MISSING)
            if val is _MISSING:
                val = self._global_val
            if val is _MISSING:
                val = default
            if val is _MISSING:
                val = self._default
            if val is _MISSING:
                raise LookupError(self)
            return val
            
        def set(self, value):
            if _is_global.get():
                orig_val = self._global_val
                self._global_val = value
                return _Token(orig_val)
            else:
                return self._var.set(value)
        
        def reset(self, token):
            if _is_global.get():
                self._global_val = token.orig_val
            else:
                self._var.reset(token)

    class _Token:
        __slots__ = ('orig_val')
        def __init__(self, orig_val):
            self.orig_val = orig_val

    def copy_context():
        ctx = _cv.copy_context()
        ctx.run(_not_global)
        return ctx

    def _not_global():
        _is_global.set(False)
        
else:
    from contextvars import *


