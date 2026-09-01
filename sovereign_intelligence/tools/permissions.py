from dataclasses import dataclass


@dataclass(frozen=True)
class ToolPermissions:
    read: bool = False
    write: bool = False
    execute: bool = False
    network: bool = False
    destructive: bool = False


@dataclass(frozen=True)
class PermissionDecision:
    allowed: bool
    reason: str


class PermissionGate:

    def __init__(
        self,
        allow_read=True,
        allow_write=False,
        allow_execute=False,
        allow_network=False,
        allow_destructive=False,
    ):
        self.allow_read = allow_read
        self.allow_write = allow_write
        self.allow_execute = allow_execute
        self.allow_network = allow_network
        self.allow_destructive = allow_destructive

    def check(self, permissions):

        if permissions.read and not self.allow_read:
            return PermissionDecision(False, "Read access disabled.")

        if permissions.write and not self.allow_write:
            return PermissionDecision(False, "Write access disabled.")

        if permissions.execute and not self.allow_execute:
            return PermissionDecision(False, "Execution access disabled.")

        if permissions.network and not self.allow_network:
            return PermissionDecision(False, "Network access disabled.")

        if permissions.destructive and not self.allow_destructive:
            return PermissionDecision(False, "Destructive access disabled.")

        return PermissionDecision(True, "Permission granted.")
