# TODO: decide whether or not to use this!

import warnings
import conifer.syrup.integration as HOOKS

__all__ = ['callhook', 'callhook_required', 'gethook']

def gethook(name, default=None):
    print dir(HOOKS)
    print (name, getattr(HOOKS, name))
    return getattr(HOOKS, name) or default

def callhook_required(name, *args, **kwargs):
    f = getattr(HOOKS, name)
    assert f, 'implementation for hook %r required but not found' % name
    return f(*args, **kwargs)

def callhook(name, *args, **kwargs):
    f = getattr(HOOKS, name)
    if f:
        return f(*args, **kwargs)