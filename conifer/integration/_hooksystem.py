# TODO: decide whether or not to use this!

import warnings

__all__ = ['hook', 'callhook', 'callhook_required', 'gethook']

__HOOKS = {}

def __register_hook(name, func):
    assert isinstance(name, basestring)
    assert callable(func)
    if name in __HOOKS:
        warnings.warn('redefining hook %r (%r)' % (name, func))
    __HOOKS[name] = func
    return func

def hook(*args):
    if isinstance(args[0], basestring):
        return lambda f: __register_hook(args[0], f)
    else:
        f = args[0]
        return __register_hook(f.__name__, f)

def gethook(name, default=None):
    return __HOOKS.get(name, default)

def callhook_required(name, *args, **kwargs):
    f = __HOOKS.get(name)
    assert f, 'implementation for hook %r required but not found' % name
    return f(*args, **kwargs)

def callhook(name, *args, **kwargs):
    f = __HOOKS.get(name)
    if f:
        return f(*args, **kwargs)

