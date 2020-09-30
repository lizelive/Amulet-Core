from typing import Tuple

from amulet.api.history.base.active_history_manager import ActiveHistoryManager
from amulet.api.history.manager.container import ContainerHistoryManager

SnapshotType = Tuple[ActiveHistoryManager, ...]


class MetaHistoryManager(ContainerHistoryManager):
    def __init__(self):
        super().__init__()
        self._world_managers = []
        self._non_world_managers = []

    def _check_snapshot(self, snapshot: SnapshotType):
        assert isinstance(snapshot, tuple) and all(
            isinstance(item, ActiveHistoryManager) for item in snapshot
        )

    def register(self, manager: ActiveHistoryManager, is_world_manager: bool):
        """
        Register a manager to track.
        :param manager: The manager to track
        :param is_world_manager: Is the manager tracking world data
        :return:
        """
        assert isinstance(
            manager, ActiveHistoryManager
        ), "manager must be an instance of BaseHistoryManager"
        if is_world_manager:
            self._world_managers.append(manager)
        else:
            self._non_world_managers.append(manager)

    def _undo(self, snapshot: SnapshotType):
        for item in snapshot:
            item.undo()

    def _redo(self, snapshot: SnapshotType):
        for item in snapshot:
            item.redo()

    def _mark_saved(self):
        for manager in self._managers(True, True):
            manager.mark_saved()

    def _managers(self, world: bool, non_world: bool) -> Tuple[ActiveHistoryManager, ...]:
        return (
            tuple(self._world_managers) * world
            + tuple(self._non_world_managers) * non_world
        )

    @property
    def changed(self) -> bool:
        if super().changed:
            return True
        managers = self._managers(True, False)
        for manager in managers:
            if manager.changed:
                return True
        return False

    def create_undo_point(self, non_world_only=False) -> bool:
        managers = self._managers(not non_world_only, True)
        snapshot = []
        for manager in managers:
            if manager.create_undo_point():
                snapshot.append(manager)
        return self._register_snapshot(tuple(snapshot))

    def restore_last_undo_point(self):
        for manager in self._managers(True, True):
            manager.restore_last_undo_point()
