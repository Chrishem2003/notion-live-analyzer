from dataclasses import dataclass, field
from uuid import uuid4


@dataclass
class CADObject:
    kind: str
    data: dict
    id: str = field(default_factory=lambda: str(uuid4()))
    selected: bool = False


class CADDocument:

    def __init__(self):
        self.objects = []
        self.undo_stack = []
        self.redo_stack = []

    def snapshot(self):
        return [
            CADObject(
                kind=obj.kind,
                data=dict(obj.data),
                id=obj.id,
                selected=obj.selected
            )
            for obj in self.objects
        ]

    def save_history(self):
        self.undo_stack.append(self.snapshot())

        if len(self.undo_stack) > 100:
            self.undo_stack.pop(0)

        self.redo_stack.clear()

    def add(self, obj):
        self.save_history()
        self.objects.append(obj)

    def clear_selection(self):
        for obj in self.objects:
            obj.selected = False

    def select(self, obj_id):
        self.clear_selection()

        for obj in self.objects:
            if obj.id == obj_id:
                obj.selected = True
                return obj

        return None

    def delete_selected(self):
        selected = [obj for obj in self.objects if obj.selected]

        if not selected:
            return False

        self.save_history()

        self.objects = [
            obj for obj in self.objects
            if not obj.selected
        ]

        return True

    def undo(self):
        if not self.undo_stack:
            return False

        self.redo_stack.append(self.snapshot())
        self.objects = self.undo_stack.pop()

        return True

    def redo(self):
        if not self.redo_stack:
            return False

        self.undo_stack.append(self.snapshot())
        self.objects = self.redo_stack.pop()

        return True
