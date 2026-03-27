# 한성대 E-class 출석/과제 확인 스킬

한성대학교 e-class에서 **출석 현황**과 **과제/퀴즈/토론 상태**를 읽기 전용으로 점검하는 스크립트 모음입니다.

## 지원 기능

- `진도현황` 표 기반 과목별 출석 조회
- 학습활동 링크 자동 수집
  - 과제: `/mod/assign/view.php?id=`
  - 퀴즈: `/mod/quiz/view.php?id=`
  - 토론: `/mod/forum/view.php?id=`
- 현재 시점까지 누적된 주차 기준으로 과제/퀴즈/토론 상태 조회
- 마감일 / 제출상태 / 응시상태 / 참여상태 추출

## 스크립트

### 1) 출석 현황
```bash
python3 scripts/eclass_attendance_report.py --open-only
```

### 2) 과제/퀴즈/토론 현황
```bash
python3 scripts/eclass_coursework_report.py
```

특정 과목만 확인:
```bash
python3 scripts/eclass_coursework_report.py --course-url "https://learn.hansung.ac.kr/course/view.php?id=44909"
```

JSON 출력:
```bash
python3 scripts/eclass_coursework_report.py --json
```

## 동작 방식

### 출석 현황
- 과목 페이지의 `진도현황` 표를 직접 읽습니다.
- 각 주차를 `출석 / 결석 / - / unknown` 으로 판정합니다.

### 과제/퀴즈/토론 현황
- 과목 페이지에서 관련 학습활동 링크를 찾습니다.
- 항목별 상세 페이지에 들어가서 상태를 판정합니다.
- 현재 주차는 `진도현황` 표에서 **처음 `-` 가 나온 주차의 직전 주차**로 계산합니다.
- 최종적으로는 **실행 시점까지 누적된 주차**의 항목만 보고합니다.

## 환경 변수
프로젝트 루트의 `.env` 예시:

```env
HANSUNG_INFO_ID=your_id
HANSUNG_INFO_PASSWORD=your_password
```

## 참고

- 이 저장소는 **읽기 전용 점검/조회용**입니다.
- 퀴즈/토론 상태 판정은 실제 페이지 문구를 기준으로 지속 보정 중입니다.
- 학교 페이지 구조가 바뀌면 selector / 문구 매핑을 함께 수정해야 합니다.
