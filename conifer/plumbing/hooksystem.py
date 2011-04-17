
HOOKS = None

__all__ = ['callhook', 'callhook_required', 'gethook', 'initialize_hooks']

def initialize_hooks(obj):
    global HOOKS
    assert HOOKS is None, ('Cannot load hooksystem twice. '
                           'Probably you are importing "models" '
                           'using two different module paths.')
    HOOKS = obj

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
