class TransparentProxy:
    """
    A transparent proxy that forwards entirely to the underlying target object,
    except for its __call__ (and potentially invoke/generate methods) which 
    are forwarded to the wrapper_fn.
    This solves `isinstance(agent, OriginalAgentClass)` bugs silently breaking 
    type hierarchies down the pipeline.
    """
    __slots__ = ['_target', '_wrapper']

    def __init__(self, target, wrapper):
        # We use object.__setattr__ to avoid triggering our own __setattr__
        object.__setattr__(self, '_target', target)
        object.__setattr__(self, '_wrapper', wrapper)

    def __getattr__(self, name):
        return getattr(object.__getattribute__(self, '_target'), name)

    def __setattr__(self, name, value):
        setattr(object.__getattribute__(self, '_target'), name, value)

    def __call__(self, *args, **kwargs):
        # Always route __call__ through the injected wrap logic
        return object.__getattribute__(self, '_wrapper')(*args, **kwargs)

    @property
    def __class__(self):
        return object.__getattribute__(self, '_target').__class__
        
    def __instancecheck__(self, instance):
        return isinstance(instance, self.__class__)
