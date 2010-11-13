# TODO: decide whether or not to use this!

import warnings
import conifer.syrup.integration as HOOKS

__all__ = ['callhook', 'callhook_required', 'gethook']

def gethook(name, default=None):
    return getattr(HOOKS, name, None) or default

def callhook_required(name, *args, **kwargs):
    f = getattr(HOOKS, name, None)
    assert f, 'implementation for hook %r required but not found' % name
    return f(*args, **kwargs)

def callhook(name, *args, **kwargs):
    f = getattr(HOOKS, name, None)
    if f:
        return f(*args, **kwargs)
    else:
        return None
