"""
Automatic Timetable Scheduler
==============================
Constraint-satisfaction backtracking algorithm for generating
conflict-free timetables.

Hard constraints (never violated):
  - No teacher teaches two classes at the same (day, slot)
  - No room hosts two classes at the same (day, slot)
  - No section has two classes at the same (day, slot)
  - Lab subjects occupy consecutive slots
  - Teacher unavailability is respected

Soft constraints (best-effort):
  - Distribute a subject's lectures across different days
  - Prefer assigning to rooms with matching capacity
"""

from __future__ import annotations
import random
from typing import List, Dict, Tuple, Optional, Set
from dataclasses import dataclass, field


# ── Default time slots (matching the existing system) ─────────────────
DEFAULT_TIME_SLOTS = [
    "09:30|10:30",
    "10:30|11:30",
    "11:30|12:30",
    "13:30|14:30",
    "14:30|15:30",
    "15:30|16:30",
    "16:30|17:30",
]

DEFAULT_DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]


@dataclass
class ScheduleSubject:
    """Represents a subject to be scheduled."""
    id: int
    code: str
    name: str
    teacher_id: Optional[int]
    teacher_name: str
    lectures_per_week: int
    is_lab: bool
    lab_duration: int = 2  # number of consecutive slots for a lab


@dataclass
class ScheduleRoom:
    """Represents a room available for scheduling."""
    id: int
    room_number: str
    capacity: int


@dataclass
class ScheduleEntry:
    """A single placed timetable entry."""
    subject: ScheduleSubject
    room: ScheduleRoom
    day: str
    start_time: str
    end_time: str


@dataclass
class ScheduleResult:
    """Result of the scheduling algorithm."""
    success: bool
    entries: List[ScheduleEntry] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    total_placed: int = 0
    total_required: int = 0


class TimetableScheduler:
    """
    Constraint-satisfaction scheduler using backtracking with
    most-constrained-variable heuristic.
    """

    def __init__(
        self,
        subjects: List[ScheduleSubject],
        rooms: List[ScheduleRoom],
        days: List[str],
        time_slots: List[str],
        teacher_unavailable: Dict[int, Set[Tuple[str, str]]],
        existing_entries: Optional[List[dict]] = None,
    ):
        self.subjects = subjects
        self.rooms = rooms
        self.days = days
        self.time_slots = time_slots
        self.teacher_unavailable = teacher_unavailable  # teacher_id -> {(day, slot), ...}

        # occupancy trackers:  key = (day, slot_str)
        self.teacher_occupied: Dict[Tuple[str, str], Set[int]] = {}    # -> set of teacher_ids
        self.room_occupied: Dict[Tuple[str, str], Set[int]] = {}       # -> set of room_ids
        self.section_occupied: Dict[Tuple[str, str], bool] = {}        # -> True if occupied

        # track which days a subject is already placed on (for distribution)
        self.subject_days: Dict[int, List[str]] = {}

        self.placed_entries: List[ScheduleEntry] = []

        # Pre-populate occupancy from existing entries (cross-section awareness)
        if existing_entries:
            for entry in existing_entries:
                day = entry["day_of_week"]
                slot = f"{entry['start_time']}|{entry['end_time']}"
                key = (day, slot)
                tid = entry.get("teacher_id")
                rid = entry["room_id"]
                if tid:
                    self.teacher_occupied.setdefault(key, set()).add(tid)
                self.room_occupied.setdefault(key, set()).add(rid)

    def _slot_index(self, slot: str) -> int:
        """Return the index of a slot in the time_slots list."""
        try:
            return self.time_slots.index(slot)
        except ValueError:
            return -1

    def _get_consecutive_slots(self, start_idx: int, count: int) -> Optional[List[str]]:
        """Return `count` consecutive slots starting from start_idx, or None."""
        if start_idx + count > len(self.time_slots):
            return None
        slots = self.time_slots[start_idx:start_idx + count]
        # Verify they are truly consecutive (no lunch break gap)
        for i in range(len(slots) - 1):
            end_of_current = slots[i].split("|")[1]
            start_of_next = slots[i + 1].split("|")[0]
            if end_of_current != start_of_next:
                return None
        return slots

    def _is_slot_available(
        self, day: str, slot: str, teacher_id: Optional[int], room_id: int
    ) -> bool:
        """Check if a (day, slot) is available for the given teacher, room, and section."""
        key = (day, slot)

        # Section conflict
        if self.section_occupied.get(key, False):
            return False

        # Room conflict
        if room_id in self.room_occupied.get(key, set()):
            return False

        # Teacher conflict
        if teacher_id:
            if teacher_id in self.teacher_occupied.get(key, set()):
                return False
            # Teacher unavailability
            if key in self.teacher_unavailable.get(teacher_id, set()):
                return False

        return True

    def _place_entry(self, subject: ScheduleSubject, room: ScheduleRoom,
                     day: str, slot: str) -> ScheduleEntry:
        """Place an entry and update occupancy trackers."""
        key = (day, slot)
        start, end = slot.split("|")

        self.section_occupied[key] = True
        self.room_occupied.setdefault(key, set()).add(room.id)
        if subject.teacher_id:
            self.teacher_occupied.setdefault(key, set()).add(subject.teacher_id)

        self.subject_days.setdefault(subject.id, []).append(day)

        entry = ScheduleEntry(
            subject=subject,
            room=room,
            day=day,
            start_time=start,
            end_time=end,
        )
        self.placed_entries.append(entry)
        return entry

    def _remove_entry(self, entry: ScheduleEntry):
        """Remove a placed entry and restore occupancy trackers."""
        slot = f"{entry.start_time}|{entry.end_time}"
        key = (entry.day, slot)

        self.section_occupied[key] = False
        self.room_occupied.get(key, set()).discard(entry.room.id)
        if entry.subject.teacher_id:
            self.teacher_occupied.get(key, set()).discard(entry.subject.teacher_id)

        if entry.subject.id in self.subject_days:
            days_list = self.subject_days[entry.subject.id]
            if entry.day in days_list:
                days_list.remove(entry.day)

        if entry in self.placed_entries:
            self.placed_entries.remove(entry)

    def _count_available_options(self, subject: ScheduleSubject) -> int:
        """Count how many (day, slot, room) options are available for a subject."""
        count = 0
        if subject.is_lab:
            for day in self.days:
                for si in range(len(self.time_slots)):
                    consec = self._get_consecutive_slots(si, subject.lab_duration)
                    if not consec:
                        continue
                    for room in self.rooms:
                        if all(self._is_slot_available(day, s, subject.teacher_id, room.id) for s in consec):
                            count += 1
        else:
            for day in self.days:
                for slot in self.time_slots:
                    for room in self.rooms:
                        if self._is_slot_available(day, slot, subject.teacher_id, room.id):
                            count += 1
        return count

    def _build_lecture_tasks(self) -> List[Tuple[ScheduleSubject, int]]:
        """
        Build a list of (subject, lecture_number) tasks to schedule.
        Sort by most-constrained first (labs first, then fewest options).
        """
        tasks = []
        for subj in self.subjects:
            for lec_num in range(subj.lectures_per_week):
                tasks.append((subj, lec_num))

        # Sort: labs first, then by number of available options (ascending)
        option_counts = {}
        for subj in self.subjects:
            option_counts[subj.id] = self._count_available_options(subj)

        tasks.sort(key=lambda t: (
            0 if t[0].is_lab else 1,           # labs first
            option_counts.get(t[0].id, 999),    # most constrained first
        ))
        return tasks

    def _get_day_priority(self, subject: ScheduleSubject, day: str) -> int:
        """
        Lower value = higher priority (prefer days without this subject).
        This implements the 'even distribution' soft constraint.
        """
        placed_days = self.subject_days.get(subject.id, [])
        count = placed_days.count(day)
        return count

    def _solve(self, tasks: List[Tuple[ScheduleSubject, int]], idx: int) -> bool:
        """Recursive backtracking solver."""
        if idx >= len(tasks):
            return True  # All tasks placed!

        subject, lec_num = tasks[idx]

        # Build candidate placements
        candidates = []

        if subject.is_lab:
            for day in self.days:
                day_prio = self._get_day_priority(subject, day)
                for si in range(len(self.time_slots)):
                    consec = self._get_consecutive_slots(si, subject.lab_duration)
                    if not consec:
                        continue
                    for room in self.rooms:
                        if all(self._is_slot_available(day, s, subject.teacher_id, room.id) for s in consec):
                            candidates.append((day_prio, day, consec, room))
        else:
            for day in self.days:
                day_prio = self._get_day_priority(subject, day)
                for slot in self.time_slots:
                    for room in self.rooms:
                        if self._is_slot_available(day, slot, subject.teacher_id, room.id):
                            candidates.append((day_prio, day, [slot], room))

        # Sort candidates: prefer days where this subject isn't yet placed
        candidates.sort(key=lambda c: c[0])

        # Shuffle within same priority for variety
        grouped: Dict[int, list] = {}
        for c in candidates:
            grouped.setdefault(c[0], []).append(c)
        sorted_candidates = []
        for prio in sorted(grouped.keys()):
            group = grouped[prio]
            random.shuffle(group)
            sorted_candidates.extend(group)

        for _prio, day, slots, room in sorted_candidates:
            # Place all slots for this lecture
            placed = []
            for slot in slots:
                entry = self._place_entry(subject, room, day, slot)
                placed.append(entry)

            # Recurse
            if self._solve(tasks, idx + 1):
                return True

            # Backtrack
            for entry in reversed(placed):
                self._remove_entry(entry)

        return False

    def generate(self) -> ScheduleResult:
        """Run the scheduler and return the result."""
        result = ScheduleResult(success=False)

        if not self.subjects:
            result.warnings.append("No subjects to schedule.")
            result.success = True
            return result

        if not self.rooms:
            result.warnings.append("No rooms available.")
            return result

        # Calculate total required slots
        total_required = 0
        for subj in self.subjects:
            if subj.is_lab:
                total_required += subj.lectures_per_week * subj.lab_duration
            else:
                total_required += subj.lectures_per_week
        result.total_required = total_required

        # Check capacity
        total_available = len(self.days) * len(self.time_slots)
        if total_required > total_available:
            result.warnings.append(
                f"Warning: {total_required} slots needed but only {total_available} "
                f"slots available ({len(self.days)} days × {len(self.time_slots)} slots). "
                f"Some subjects may not be placed."
            )

        # Build tasks and solve
        tasks = self._build_lecture_tasks()
        random.seed(42)  # deterministic for reproducibility

        success = self._solve(tasks, 0)

        result.entries = list(self.placed_entries)
        result.total_placed = len(set(
            (e.day, f"{e.start_time}|{e.end_time}") for e in self.placed_entries
        ))
        result.success = success

        if not success:
            # Figure out what wasn't placed
            placed_subjects = {}
            for e in self.placed_entries:
                placed_subjects.setdefault(e.subject.id, 0)
                if not e.subject.is_lab:
                    placed_subjects[e.subject.id] += 1
                else:
                    placed_subjects[e.subject.id] = max(
                        placed_subjects[e.subject.id],
                        1  # count lab sessions, not individual slots
                    )

            for subj in self.subjects:
                placed_count = placed_subjects.get(subj.id, 0)
                if placed_count < subj.lectures_per_week:
                    result.warnings.append(
                        f"Could only place {placed_count}/{subj.lectures_per_week} "
                        f"lectures for {subj.code} ({subj.name})."
                    )

            # Try partial placement — keep what we have
            result.success = len(self.placed_entries) > 0
            if self.placed_entries:
                result.warnings.insert(0,
                    "Partial timetable generated. Not all subjects could be fully placed."
                )

        return result


def run_scheduler(
    subjects_data: list,
    rooms_data: list,
    days: List[str],
    time_slots: List[str],
    teacher_unavailable: Dict[int, List[dict]],
    existing_entries: Optional[List[dict]] = None,
) -> ScheduleResult:
    """
    Convenience function to run the scheduler from raw data dicts.

    Args:
        subjects_data: list of dicts with keys: id, code, name, teacher_id,
                       teacher_name, lectures_per_week, is_lab, lab_duration
        rooms_data: list of dicts with keys: id, room_number, capacity
        days: list of day names
        time_slots: list of slot strings like "09:30|10:30"
        teacher_unavailable: dict mapping teacher_id -> list of
                             {"day": "Monday", "slot": "09:30|10:30"}
        existing_entries: optional list of dicts representing entries from
                          other sections (for cross-section conflict detection).
    """
    subjects = [
        ScheduleSubject(
            id=s["id"],
            code=s["code"],
            name=s["name"],
            teacher_id=s.get("teacher_id"),
            teacher_name=s.get("teacher_name", ""),
            lectures_per_week=s.get("lectures_per_week", 3),
            is_lab=s.get("is_lab", False),
            lab_duration=s.get("lab_duration", 2),
        )
        for s in subjects_data
    ]

    rooms = [
        ScheduleRoom(
            id=r["id"],
            room_number=r["room_number"],
            capacity=r["capacity"],
        )
        for r in rooms_data
    ]

    # Convert teacher unavailability to sets of (day, slot) tuples
    unavail_sets: Dict[int, Set[Tuple[str, str]]] = {}
    for tid, slots in teacher_unavailable.items():
        unavail_sets[tid] = {(s["day"], s["slot"]) for s in slots}

    scheduler = TimetableScheduler(
        subjects=subjects,
        rooms=rooms,
        days=days,
        time_slots=time_slots or DEFAULT_TIME_SLOTS,
        teacher_unavailable=unavail_sets,
        existing_entries=existing_entries,
    )

    return scheduler.generate()
