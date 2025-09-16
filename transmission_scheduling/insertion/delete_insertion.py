from scheduling_model import OT, GSTW, BT, TTW, TW
from transmission_scheduling.conflict_checks import getConflictingTasks
from transmission_scheduling.input_parameters import TransmissionParams
from transmission_scheduling.insertion.insertion_interface import InsertionInterface
from transmission_scheduling.insertion.direct_insertion import DirectInsertion


class DeleteInsertion(InsertionInterface):

    def __init__(self, parameters: TransmissionParams):
        """
        Initialize the DirectInsertion class with the given parameters.
        """
        self.p = parameters
        self.direct_insert = DirectInsertion(parameters)

    def generateBuffer(self, otToBuffer: OT, gstwToDownlink: GSTW, otListPrioritySorted: list[OT], btList: list[BT],
                       gstwList: list[GSTW], ttwList: list[TTW] = None) -> tuple[BT | None, list[OT], list[BT]]:
        """
        Try to insert the buffering of an observed target into the schedule by deleting other observation tasks if necessary.

        Args:
            otToBuffer (OT): The observation task to schedule buffering for.
            gstwToDownlink (GSTW): The ground station time window to use for downlinking the buffered data.
            otListPrioritySorted (list[OT]): List of all observation tasks, sorted by priority (highest priority first)
            btList (list[BT]): List of all already scheduled buffering tasks.
            gstwList (list[GSTW]): List of all ground station time windows.
            ttwList (list[TTW]): List of all target time windows.

        Returns:
            tuple[BT | None, list[OT], list[BT]]: A tuple containing:

                - BT | None: The scheduled buffering task, or None if no valid scheduling was found.
                - list[OT]: Modified list of observation tasks, with any deleted tasks removed.
                - list[BT]: Unchanged list of buffering tasks.
        """

        p = self.p

        # Remove lower priority observation tasks until a valid insertion is found
        otListPrioSorted = otListPrioritySorted.copy()
        otIndex = otListPrioSorted.index(otToBuffer)
        otListLength = len(otListPrioSorted)
        nRemove = otListLength - otIndex  # The number of observation tasks we can remove
        found = False
        for i in range(0, nRemove):
            otListMod = otListPrioSorted[:otListLength - i]
            bt, _, _ = self.direct_insert.generateBuffer(otToBuffer, gstwToDownlink, otListMod, btList, gstwList)
            if bt is not None:
                found = True
                break

        if not found:
            return None, otListPrioSorted, btList

        # Only remove the observation tasks that are needed to fit the buffering task
        bufferTimeWindow = TW(bt.start, bt.end + p.interTaskTime)
        conflictOTs, conflictBTs, conflictGSTWs = getConflictingTasks(bufferTimeWindow, btList, otListPrioSorted,
                                                                      gstwList, p)
        if conflictBTs or conflictGSTWs:
            # We can only remove observation tasks, if there are conflicts with other tasks, return None
            return None, otListPrioSorted, btList

        # Remove the observation tasks that conflict with the buffering task
        for conflictOT in conflictOTs:
            # print which task has been removed
            id = otListPrioSorted.index(conflictOT) + 1
            print(
                f"Removed observation task {id} at {conflictOT.start} to fit buffering task for {otToBuffer.GT.id} at {otToBuffer.start}")
            otListPrioSorted.remove(conflictOT)

        return bt, otListPrioSorted, btList