from jaclang.plugin.default import hookimpl
from jaclang.plugin.spec import ArchBound, WalkerArchitype, DSFunc

from dataclasses import dataclass
from functools import wraps
from typing import Type, Callable


class JacFeature:
    @staticmethod
    @hookimpl
    def make_walker(
        on_entry: list[DSFunc], on_exit: list[DSFunc]
    ) -> Callable[[type], type]:
        """Create a walker architype."""

        def decorator(cls: Type[ArchBound]) -> Type[ArchBound]:
            """Decorate class."""
            cls = dataclass(eq=False)(cls)
            for i in on_entry + on_exit:
                i.resolve(cls)
            arch_cls = WalkerArchitype
            if not issubclass(cls, arch_cls):
                cls = type(cls.__name__, (cls, arch_cls), {})
            cls._jac_entry_funcs_ = on_entry
            cls._jac_exit_funcs_ = on_exit
            inner_init = cls.__init__

            @wraps(inner_init)
            def new_init(self: ArchBound, *args: object, **kwargs: object) -> None:
                inner_init(self, *args, **kwargs)
                arch_cls.__init__(self)

            cls.__init__ = new_init
            print("IM IN THE PLUGIN YO!")
            return cls

        print("IM IN THE PLUGIN YO!")
        return decorator
