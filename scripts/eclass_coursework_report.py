#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import time
from pathlib import Path

from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

LOGIN_URL = 'https://learn.hansung.ac.kr/login/index.php'
UBION_URL = 'https://learn.hansung.ac.kr/local/ubion/user/'
BASE_URL = 'https://learn.hansung.ac.kr'

ITEM_PATTERNS = {
    'quiz': '/mod/quiz/view.php?id=',
    'forum': '/mod/forum/view.php?id=',
    'assign': '/mod/assign/view.php?id=',
    'ubboard': '/mod/ubboard/view.php?id=',
    'ubfile': '/mod/ubfile/view.php?id=',
    'url': '/mod/url/view.php?id=',
    'vod': '/mod/vod/view.php?id=',
}


def load_env_if_present():
    candidate_paths = [
        Path.cwd() / '.env',
        Path('/home/ubuntu/.openclaw/.env'),
        Path('/home/ubuntu/.openclaw/workspace/.env'),
    ]
    for env_path in candidate_paths:
        if env_path.exists():
            for line in env_path.read_text(encoding='utf-8').splitlines():
                line = line.strip()
                if not line or line.startswith('#') or '=' not in line:
                    continue
                k, v = line.split('=', 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def login(page, username, password):
    page.goto(LOGIN_URL)
    page.wait_for_selector('form')
    page.fill('input[name="username"]', username)
    page.fill('input[name="password"]', password)
    page.click('button[type=submit], input[name=loginbutton]')
    page.wait_for_load_state('networkidle')
    time.sleep(1)


def find_courses_from_ubion(page):
    page.goto(UBION_URL)
    page.wait_for_load_state('networkidle')
    soup = BeautifulSoup(page.content(), 'html.parser')
    courses = []
    for a in soup.find_all('a', href=True):
        href = a['href']
        if 'course/view.php' not in href:
            continue
        if 'id=46668' in href:
            continue
        title = a.get_text().strip()
        full = href if href.startswith('http') else BASE_URL + href
        if not any(c['href'] == full for c in courses):
            courses.append({'title': title, 'href': full})
    return courses


def parse_week_label(text):
    patterns = [
        r'(\d+)\s*주차',
        r'(\d+)\s*Week',
        r'Lecture\s*(\d+)',
        r'\[Lecture\s*(\d+)\]',
        r'(\d+)장\)',
        r'실습\s*(\d+)\)',
        r'(?:과거|기말|중간|프로젝트).*?(\d+)주차',
    ]
    for pattern in patterns:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            try:
                return int(m.group(1))
            except Exception:
                continue
    return None


def is_actionable_candidate(item_type, title):
    text = (title or '').strip()
    if not text:
        return False

    exclude_keywords = [
        '이용안내', '공지사항', '한성대 공지사항', 'q&a', 'faq', '강좌 q&a', '강의자료 게시판',
        '수업 중 질문에 대한 답변 게시판', '강의내용 q&a 게시판', '더보기', '저작권', '홈페이지',
        '구매사이트', '결과물', '오리엔테이션', '강의교안', 'lecture', 'lab', 'solution', '파일'
    ]
    lowered = text.lower()
    if any(k.lower() in lowered for k in exclude_keywords):
        return False

    if item_type in {'assign', 'quiz', 'forum'}:
        return True

    include_keywords = ['과제', '제출', '퀴즈', '토론', '보고서', '기말', '중간', '시험']
    return any(k in text for k in include_keywords)


def discover_coursework_links(html):
    soup = BeautifulSoup(html, 'html.parser')
    items = []
    seen = set()
    for a in soup.find_all('a', href=True):
        href = a['href']
        item_type = None
        for kind, needle in ITEM_PATTERNS.items():
            if needle in href:
                item_type = kind
                break
        if not item_type:
            continue
        full = href if href.startswith('http') else BASE_URL + href
        if full in seen:
            continue
        title = a.get_text(' ', strip=True) or item_type
        if not is_actionable_candidate(item_type, title):
            continue
        seen.add(full)
        week_label = None
        context = title
        try:
            for ancestor in a.parents:
                if getattr(ancestor, 'name', None) not in ['li', 'div', 'section', 'ul', 'article']:
                    continue
                text_blob = ancestor.get_text(separator=' ', strip=True)
                if not text_blob or len(text_blob) >= 3000:
                    continue
                guessed = parse_week_label(text_blob)
                if guessed is not None:
                    week_label = guessed
                    context = text_blob
                    break
        except Exception:
            pass
        if week_label is None:
            week_label = parse_week_label(title)
        if week_label is None and context:
            week_label = parse_week_label(context)
        items.append({'type': item_type, 'title': title, 'href': full, 'week_label': week_label, 'context': context})
    return items


def extract_due_date(text):
    table_patterns = [
        r'종료\s*일시\s*(\d{4}-\d{2}-\d{2}\s*\d{2}:\d{2})',
        r'마감\s*일시\s*(\d{4}-\d{2}-\d{2}\s*\d{2}:\d{2})',
        r'종료\s*일시\s*(\d{4}\.\d{2}\.\d{2}\s*\d{2}:\d{2})',
        r'마감\s*일시\s*(\d{4}\.\d{2}\.\d{2}\s*\d{2}:\d{2})',
    ]
    for pattern in table_patterns:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            return ' '.join(m.group(1).split())

    patterns = [
        r'(?:마감일|제출기한|종료일|Due date|Due)\s*[:：]?\s*([^\n]+)',
        r'(\d{4}-\d{2}-\d{2}\s*\d{2}:\d{2})',
        r'(\d{4}\.\d{2}\.\d{2}\s*\([^)]*\)?\s*\d{2}:\d{2})',
        r'(\d{4}년\s*\d{1,2}월\s*\d{1,2}일\s*\d{1,2}:\d{2})',
    ]
    for pattern in patterns:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            return ' '.join(m.group(1).split())
    return None


def infer_status(item_type, text):
    normalized = ' '.join(text.split())
    status_map = {
        'quiz': [
            ('응시 완료', ['응시 완료', '제출 완료', '제출됨', '완료됨', '시도 완료', '재응시 불가', '종료됨', '피드백 보기', '답안 제출 기회를 모두 사용하였습니다', '최종 점수는']),
            ('미응시', ['아직 응시하지 않았', '미응시', '응시 필요', '시도 없음']),
        ],
        'forum': [],
        'assign': [
            ('제출 완료', ['제출 완료', '제출됨', '채점 대기', '제출한 과제']),
            ('미제출', ['제출 안 함', '미제출', '제출 필요', '제출되지 않았']),
        ],
    }
    for label, needles in status_map.get(item_type, []):
        if any(needle in normalized for needle in needles):
            return label

    if item_type == 'forum':
        return '토론 있음'
    if item_type == 'quiz':
        if any(k in normalized for k in ['종료됨', '제출됨', '피드백 보기', '답안 제출 기회를 모두 사용하였습니다', '최종 점수는']):
            return '응시 완료'
        if '답안 제출 가능 횟수' in normalized and not any(k in normalized for k in ['종료됨', '제출됨', '피드백 보기', '최종 점수는']):
            return '미응시'
    return '확인 실패'


def inspect_coursework_item(page, item):
    try:
        page.goto(item['href'])
        page.wait_for_load_state('networkidle')
        text = page.inner_text('body')
    except Exception as e:
        return {
            'type': item['type'],
            'title': item['title'],
            'href': item['href'],
            'due': None,
            'status': '확인 실패',
            'error': str(e),
        }
    due = extract_due_date(text)
    status = infer_status(item['type'], text)
    return {
        'type': item['type'],
        'title': item['title'],
        'href': item['href'],
        'due': due,
        'status': status,
    }


def detect_current_week_from_attendance(page):
    try:
        items = page.query_selector_all('ul.attendance li.attendance_section')
        weeks = []
        for item in items:
            week_el = item.query_selector('p.sname')
            if not week_el:
                continue
            week = int(week_el.inner_text().strip())
            text = item.inner_text().strip()
            weeks.append((week, text))
        weeks.sort(key=lambda x: x[0])
        for week, text in weeks:
            if '-' in text:
                return max(1, week - 1)
        attended = [week for week, text in weeks if '출석' in text or '결석' in text]
        if attended:
            return max(attended)
    except Exception:
        pass
    return None


def build_report(course_summaries, as_json=False):
    if as_json:
        return json.dumps(course_summaries, ensure_ascii=False, indent=2)

    lines = []
    lines.append('E-class 과제/퀴즈/토론 현황')
    lines.append('')
    actionable = []
    for course in course_summaries:
        lines.append(f"- {course['course']}")
        if not course['items']:
            lines.append('  - 실행 시점까지 해당되는 제출/응시/참여 항목 없음')
            continue
        for item in course['items']:
            due = item['due'] or '마감일 확인 실패'
            week = item.get('week_label')
            week_txt = f'{week}주차 | ' if week is not None else ''
            lines.append(f"  - {week_txt}[{item['type']}] {item['title']} | {item['status']} | {due}")
            if item['status'] in ['미제출', '미응시', '확인 실패']:
                actionable.append((course['course'], item))
        lines.append('')

    lines.append('실행 시점까지의 미완료 체크')
    if actionable:
        for course_name, item in actionable:
            due = item['due'] or '마감일 확인 실패'
            week = item.get('week_label')
            week_txt = f'{week}주차 | ' if week is not None else ''
            lines.append(f"- {course_name} | {week_txt}[{item['type']}] {item['title']} | {item['status']} | {due}")
    else:
        lines.append('- 이번 주 미완료 항목 없음')
    return '\n'.join(lines).strip() + '\n'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--course-url')
    parser.add_argument('--json', action='store_true')
    args = parser.parse_args()

    load_env_if_present()
    username = os.environ.get('HANSUNG_INFO_ID') or os.environ.get('ECLASS_ID')
    password = os.environ.get('HANSUNG_INFO_PASSWORD') or os.environ.get('ECLASS_PASSWORD')
    if not username or not password:
        raise SystemExit('Missing Hansung credentials in .env')

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(locale='ko-KR', viewport={'width': 1280, 'height': 800})
        page = context.new_page()
        login(page, username, password)

        courses = [{'title': args.course_url, 'href': args.course_url}] if args.course_url else find_courses_from_ubion(page)
        course_summaries = []

        for course in courses:
            page.goto(course['href'])
            page.wait_for_load_state('networkidle')
            items = discover_coursework_links(page.content())
            current_week = detect_current_week_from_attendance(page)
            eligible_items = [
                item for item in items
                if current_week is None or item.get('week_label') is None or item.get('week_label') <= current_week
            ]
            if not eligible_items and items:
                eligible_items = items

            # If only URL/board assets are found, keep them through the same eligibility gate
            # but allow the report to surface week-based items up to current_week.
            inspected = []
            for item in eligible_items:
                inspected_item = inspect_coursework_item(page, item)
                inspected_item['week_label'] = item.get('week_label')
                inspected.append(inspected_item)
            course_summaries.append({
                'course': course.get('title') or course.get('href'),
                'items': inspected,
            })

        print(build_report(course_summaries, as_json=args.json))
        context.close()
        browser.close()


if __name__ == '__main__':
    main()
