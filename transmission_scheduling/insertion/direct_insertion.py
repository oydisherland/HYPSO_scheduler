from scheduling_model import OT, GSTW, BT, TTW
from transmission_scheduling.conflict_checks import bufferTaskConflicting
from transmission_scheduling.input_parameters import TransmissionParams
from transmission_scheduling.insertion.insertion_interface import InsertionInterface


class DirectInsertion(InsertionInterface):

    def __init__(self, parameters: TransmissionParams):
        """
        Initialize the DirectInsertion class with the given parameters.
        """
        self.p = parameters

    def generateBuffer(self, otToBuffer: OT, gstwToDownlink: GSTW, otList: list[OT], btList: list[BT],
                       dtList, gstwList: list[GSTW], ttwList: list[TTW] = None) -> tuple[BT | None, list[OT], list[BT]]:
        """
        Try to insert the buffering of an observed target directly into the schedule.
        Insertion is tried at the end of other tasks, so all tasks neatly follow each other.
        If no valid insertion is found, return None.

        Args:
            otToBuffer (OT): The observation task to schedule buffering for.
            gstwToDownlink (GSTW): The ground station time window to use for downlinking the buffered data.
            otList (list[OT]): List of all observation tasks
            btList (list[BT]): List of all already scheduled buffering tasks.
            dtList (list[DT]): List of all already scheduled downlinking tasks plus the candidate downlink tasks.
            gstwList (list[GSTW]): List of all ground station time windows.
            ttwList (list[TTW]): List of all target time windows.

        Returns:
            tuple[BT | None, list[OT], list[BT]]: A tuple containing:

                - BT | None: The scheduled buffering task if insertion was successful, otherwise None.
                - list[OT]: The (unchanged, in the case of direct insert) list of observation tasks.
                - list[BT]: The (unchanged, in the case of direct insert) list of buffering tasks.
        """

        p = self.p

        # We will save the latest possible candidate we find, i.e. closest to the ground station pass
        # This makes sure that as little captures as possible are in the buffer at the same time
        latestBTStartTime = -1
        latestBT = None

        # First guess is to immediately start buffering after observation
        # Candidate buffer task start and end
        btStart = otToBuffer.end + p.afterCaptureTime
        btEnd = btStart + p.bufferingTime
        candidateBT = BT(otToBuffer.taskID, -1, btStart, btEnd)
        if  btEnd < gstwToDownlink.TWs[0].start and btStart > latestBTStartTime:
            if not bufferTaskConflicting(candidateBT, btList, otList, dtList, gstwList, p):
                latestBT = candidateBT
                latestBTStartTime = btStart

        # Now try to insert the buffer task at the end of other observation tasks
        for ot in otList:
            # Candidate buffer task start and end
            btStart = ot.end + p.afterCaptureTime
            btEnd = btStart + p.bufferingTime

            if btEnd > gstwToDownlink.TWs[0].start or ot.end < otToBuffer.end:
                # Inserting the buffer tasks after this point would be after the intended downlink window has started.
                # Also skip if the candidate buffer task would be scheduled before its target observation
                continue

            if btStart < latestBTStartTime:
                # We already have a better candidate, skip this one
                continue

            candidateBT = BT(otToBuffer.taskID, -1, btStart, btEnd)
            if not bufferTaskConflicting(candidateBT, btList, otList, dtList, gstwList, p):
                latestBT = candidateBT
                latestBTStartTime = btStart

        # Now try to insert the buffer task at the end of other buffer tasks
        for bt in btList:
            # Candidate buffer task start and end
            btStart = bt.end + p.interTaskTime
            btEnd = btStart + p.bufferingTime
            if btStart < otToBuffer.end or btEnd > gstwToDownlink.TWs[0].start:
                continue

            if btStart < latestBTStartTime:
                # We already have a better candidate, skip this one
                continue

            candidateBT = BT(otToBuffer.taskID, -1, btStart, btEnd)
            if not bufferTaskConflicting(candidateBT, btList, otList, dtList, gstwList, p):
                latestBT = candidateBT
                latestBTStartTime = btStart

        # Last attempt is to insert after a ground station time window
        for gstw in gstwList:
            for tw in gstw.TWs:
                # Candidate buffer task start and end
                btStart = tw.end + p.interTaskTime
                btEnd = btStart + p.bufferingTime
                if btEnd > gstwToDownlink.TWs[0].start or btStart < otToBuffer.end:
                    continue

                if btStart < latestBTStartTime:
                    # We already have a better candidate, skip this one
                    continue

                candidateBT = BT(otToBuffer.taskID, -1, btStart, btEnd)
                if not bufferTaskConflicting(candidateBT, btList, otList, dtList, gstwList, p):
                    latestBT = candidateBT
                    latestBTStartTime = btStart


        if latestBT is not None:
            return latestBT, otList, btList

        # No valid insertions have been found, return None
        return None, otList, btList