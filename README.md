# Hansung E-class Attendance Skill

Read-only tooling for Hansung University e-class status checks.

## What it supports

- Course-by-course attendance lookup from the `진도현황` table
- Coursework discovery for:
  - assignments (`/mod/assign/view.php?id=`)
  - quizzes (`/mod/quiz/view.php?id=`)
  - forums/discussions (`/mod/forum/view.php?id=`)
- Current-week / up-to-current-week filtering based on the attendance table
- Submission / participation status parsing with due-date extraction

## Scripts

### Attendance
```bash
python3 scripts/eclass_attendance_report.py --open-only
```

### Coursework
```bash
python3 scripts/eclass_coursework_report.py
```

## Environment
Create a `.env` file with:

```env
HANSUNG_INFO_ID=your_id
HANSUNG_INFO_PASSWORD=your_password
```

## Notes

- This repo is intended for local personal automation and inspection.
- Attendance status is read directly from the course progress table.
- Coursework parsing is still being refined for quiz/forum status detection.
