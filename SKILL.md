---
name: eclass-attendance
description: Fetch Hansung University e-class attendance status and coursework status by course using local Python automation/parsing. Use when the user asks for e-class 출석 현황, wants course-by-course attendance, or wants pending coursework such as quizzes, assignments, and forums/discussions with due dates and submission status. This skill is read-only and should run the bundled scripts rather than guessing from memory.
---

# E-class Attendance

Use the bundled scripts to fetch attendance and coursework status directly from Hansung e-class.

## Run

Attendance summary:

```bash
python3 skills/eclass-attendance/scripts/eclass_attendance_report.py --open-only
```

Coursework summary (quiz / forum / assignment):

```bash
python3 skills/eclass-attendance/scripts/eclass_coursework_report.py
```

Sync unfinished coursework to Linear + Google Calendar:

```bash
python3 skills/eclass-attendance/scripts/eclass_sync_to_linear_calendar.py
```

Dry run:

```bash
python3 skills/eclass-attendance/scripts/eclass_sync_to_linear_calendar.py --dry-run
```

Optional flags:

```bash
python3 skills/eclass-attendance/scripts/eclass_attendance_report.py --json
python3 skills/eclass-attendance/scripts/eclass_coursework_report.py --course-url "https://learn.hansung.ac.kr/course/view.php?id=46337"
python3 skills/eclass-attendance/scripts/eclass_coursework_report.py --json
```

## What it does

### Attendance script
- Load Hansung credentials from `.env`
- Log in to e-class
- Discover courses from the Ubion course list
- Read the `진도현황` attendance table directly
- Map each week to `출석 / 결석 / - / unknown`

### Coursework script
- Discover course pages
- Parse coursework links for:
  - quiz: `/mod/quiz/view.php?id=`
  - forum/discussion: `/mod/forum/view.php?id=`
  - assignment: `/mod/assign/view.php?id=`
- Visit each item page and extract:
  - item type
  - title
  - due date / open-close period when visible
  - submission or participation status when visible
- Group results by course
- Use attendance table progression to estimate the current study week and report cumulative items up to that point

### Sync script
- Read coursework JSON output
- Keep only unfinished items (`미제출`, `미응시`, `미참여`)
- Skip overdue items
- Skip duplicates already present in Linear or Google Calendar
- Create new items as **Todo** with priority applied via Linear issue creation
- Create matching Google Calendar events with Linear links in the description

## Response style

When answering the user:
- Summarize by course first
- For attendance, keep it week-based
- For coursework, show only actionable items first (미제출 / 미응시 / 미참여 / 진행 필요)
- Include due dates when available
- If parsing fails, say `확인 실패`

## Notes

- This skill is read-only.
- Attendance and coursework should be treated as separate reports even if they are later combined into one summary.
