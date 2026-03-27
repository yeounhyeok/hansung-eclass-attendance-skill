#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path

from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

LOGIN_URL = 'https://learn.hansung.ac.kr/login/index.php'
UBION_URL = 'https://learn.hansung.ac.kr/local/ubion/user/'


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
        full = href if href.startswith('http') else 'https://learn.hansung.ac.kr' + href
        if not any(c['href'] == full for c in courses):
            courses.append({'title': title, 'href': full})
    return courses


def read_attendance_table(page):
    rows = []
    items = page.query_selector_all('ul.attendance li.attendance_section')
    for item in items:
        try:
            week_el = item.query_selector('p.sname')
            if not week_el:
                continue
            week_raw = week_el.inner_text().strip()
            week = int(week_raw)
            text = item.inner_text().strip()
            if '출석' in text:
                status = '출석'
            elif '결석' in text:
                status = '결석'
            elif '-' in text:
                status = '-'
            else:
                status = 'unknown'
            rows.append({'week': week, 'status': status})
        except Exception:
            continue
    return rows


def build_report(course_summaries, as_json=False, open_only=False):
    if open_only:
        normalized = []
        for course in course_summaries:
            active = [r for r in course['weeks'] if r['status'] != '-']
            normalized.append({'course': course['course'], 'weeks': active})
    else:
        normalized = course_summaries

    missing = []
    for course in normalized:
        for item in course['weeks']:
            if item['status'] != '출석':
                missing.append({'course': course['course'], 'week': item['week'], 'status': item['status']})

    if as_json:
        return json.dumps({'courses': normalized, 'missing': missing}, ensure_ascii=False, indent=2)

    lines = []
    lines.append('E-class 출석 현황')
    lines.append('')
    for course in normalized:
        lines.append(f"- {course['course']}")
        if not course['weeks']:
            lines.append('  - 표시할 주차 없음')
            continue
        for item in course['weeks']:
            lines.append(f"  - {item['week']}주차 | {item['status']}")
        lines.append('')

    lines.append('미출석 체크')
    if missing:
        for item in missing:
            lines.append(f"- {item['course']} | {item['week']}주차 | {item['status']}")
    else:
        lines.append('- 미출석 과목 없음')
    return '\n'.join(lines).strip() + '\n'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--course-url')
    parser.add_argument('--json', action='store_true')
    parser.add_argument('--open-only', action='store_true', help='show only weeks not marked as -')
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
            weeks = read_attendance_table(page)
            course_summaries.append({
                'course': course.get('title') or course.get('href'),
                'weeks': weeks,
            })

        print(build_report(course_summaries, as_json=args.json, open_only=args.open_only))
        context.close()
        browser.close()


if __name__ == '__main__':
    main()
