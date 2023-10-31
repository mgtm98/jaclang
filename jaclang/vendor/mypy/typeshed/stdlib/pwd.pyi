import sys
from _typeshed import structseq
from typing import Any
from typing_extensions import Final, final

if sys.platform != "win32":
    @final
    class struct_passwd(structseq[Any], tuple[str, str, int, int, str, str, str]):
        if sys.version_info >= (3, 10):
            __match_args__: Final = (
                "pw_name",
                "pw_passwd",
                "pw_uid",
                "pw_gid",
                "pw_gecos",
                "pw_dir",
                "pw_shell",
            )
        @property
        def pw_name(self) -> str: ...
        @property
        def pw_passwd(self) -> str: ...
        @property
        def pw_uid(self) -> int: ...
        @property
        def pw_gid(self) -> int: ...
        @property
        def pw_gecos(self) -> str: ...
        @property
        def pw_dir(self) -> str: ...
        @property
        def pw_shell(self) -> str: ...

    def getpwall() -> list[struct_passwd]: ...
    def getpwuid(__uid: int) -> struct_passwd: ...
    def getpwnam(__name: str) -> struct_passwd: ...