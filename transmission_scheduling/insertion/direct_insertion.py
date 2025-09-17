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
                       gstwList: list[GSTW], ttwList: list[TTW] = None) -> tuple[BT | None, list[OT], list[BT]]:
        """
        Try to insert the buffering of an observed target directly into the schedule.
        Insertion is tried at the end of other tasks, so all tasks neatly follow each other.
        If no valid insertion is found, return None.

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
                - list[OT]: The (unchanged, in the case of direct insert) list of observation tasks.
                - list[BT]: The (unchanged, in the case of direct insert) list of buffering tasks.
        """

        p = self.p

        # We will save all the possible candidates and later pick the best
        candidateBTList: list[BT] = []

        # First guess is to immediately start buffering after observation
        # Candidate buffer task start and end
        btStart = otToBuffer.end + p.afterCaptureTime
        btEnd = btStart + p.bufferingTime
        candidateBT = BT(otToBuffer.GT, btStart, btEnd)
        if not bufferTaskConflicting(candidateBT, btList, otList, gstwList, p) \
                and btEnd < gstwToDownlink.TWs[0].start:
            candidateBTList.append(candidateBT)

        # Now try to insert the buffer task at the end of other observation tasks
        for ot in otList:
            # Candidate buffer task start and end
            btStart = ot.end + p.afterCaptureTime
            btEnd = btStart + p.bufferingTime

            if btStart - otToBuffer.end > p.maxBufferOffset or btEnd > gstwToDownlink.TWs[0].start:
                # Inserting the buffer tasks after this point would be too far from the observation task
                # or be after the intended downlink window has started.
                continue
            if ot.end < otToBuffer.end:
                # Skip if the candidate buffer task would be scheduled before its target observation
                continue

            candidateBT = BT(otToBuffer.GT, btStart, btEnd)
            if not bufferTaskConflicting(candidateBT, btList, otList, gstwList, p):
                candidateBTList.append(candidateBT)
                continue

        # Now try to insert the buffer task at the end of other buffer tasks
        for bt in btList:
            # Candidate buffer task start and end
            btStart = bt.end + p.interTaskTime
            btEnd = btStart + p.bufferingTime
            if btStart - otToBuffer.end > p.maxBufferOffset or btStart < otToBuffer.end \
                    or btEnd > gstwToDownlink.TWs[0].start:
                continue

            candidateBT = BT(otToBuffer.GT, btStart, btEnd)
            if not bufferTaskConflicting(candidateBT, btList, otList, gstwList, p):
                candidateBTList.append(candidateBT)

        # Last attempt is to insert after a ground station time window
        for gstw in gstwList:
            for tw in gstw.TWs:
                # Candidate buffer task start and end
                btStart = tw.end + p.interTaskTime
                btEnd = btStart + p.bufferingTime
                if btStart - otToBuffer.end > p.maxBufferOffset or btEnd > gstwToDownlink.TWs[0].start:
                    # Inserting the buffer tasks after this point would be too far from the observation task
                    # or be after the intended downlink window has started.
                    continue
                if btStart < otToBuffer.end:
                    continue

                candidateBT = BT(otToBuffer.GT, btStart, btEnd)
                if not bufferTaskConflicting(candidateBT, btList, otList, gstwList, p):
                    candidateBTList.append(candidateBT)
                    continue

        # Choose the buffer candidate closest to the ground station pass, i.e. the one with the latest start time
        # This makes sure that as little captures as possible are in the buffer at the same time
        # TODO figure out if min or max is best (also in combination with the other settings)
        if candidateBTList:
            bestBT = max(candidateBTList, key=lambda x: x.start)
            return bestBT, otList, btList

        # No valid insertions have been found, return None
        return None, otList, btList