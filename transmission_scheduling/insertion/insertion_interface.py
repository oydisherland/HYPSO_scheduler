from abc import ABC, abstractmethod

from scheduling_model import OT, GSTW, BT, TTW

class InsertionInterface(ABC):
    @abstractmethod
    def generateBuffer(self, otToBuffer: OT, gstwToDownlink: GSTW, otList: list[OT], btList: list[BT], gstwList: list[GSTW],
                       ttwList: list[TTW] = None) -> tuple[BT | None, list[OT], list[BT]]:
        """
        Try to insert the buffering of an observed target into the schedule.

        Args:
            otToBuffer (OT): The observation task to schedule buffering for.
            gstwToDownlink (GSTW): The ground station time window to use for downlinking the buffered data.
            otList (list[OT]): List of all observation tasks
            btList (list[BT]): List of all already scheduled buffering tasks.
            gstwList (list[GSTW]): List of all ground station time windows.
            ttwList (list[TTW]): List of all target time windows.

        Returns:
            tuple[BT | None, list[OT], list[BT]]: A tuple containing:

                - BT | None: The scheduled buffering task if insertion was successful, otherwise None.
                - list[OT]: The (possibly changed) list of observation tasks.
                - list[BT]: The (possibly changed) list of buffering tasks.
        """
        pass