#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Static site generator for KIMGISA LAB renewal prototype."""
import os
import re
import csv
import io
import html as html_lib
import urllib.request
import urllib.parse

ROOT = os.path.dirname(os.path.abspath(__file__))

# ---------------------------------------------------------------------------
# CONTACT FORM (Google Apps Script Web App)
# apps-script/Code.gs 를 구글 계정에 배포한 뒤 발급되는 웹앱 URL
# (https://script.google.com/macros/s/xxxx/exec 형태)을 아래 값에 넣으면
# 투자 검토 요청 폼 제출 시 사업계획서 PDF 첨부와 함께 IR@kimgisacompany.com으로
# 자동 전송됩니다. 자세한 배포 절차는 apps-script/Code.gs 상단 주석 참고.
# ---------------------------------------------------------------------------
APPS_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbwunGaLIDkzV08bGso-THKjM0YFFsZq54d9Qc_mZ4aa_Xxfw5RkFBl4p0BQUkCd_pg/exec"

def _clean_text(s):
    return html_lib.unescape(s or "").strip()

def _safe_html_text(s):
    return html_lib.escape(s or "", quote=False)

# ---------------------------------------------------------------------------
# PORTFOLIO SHEET SYNC
# 김기사랩 팀이 관리하는 구글 시트(회사명/한줄소개/로고 URL/홈페이지 URL/노출여부)를
# 빌드 시점에 읽어와서 기존 PORTFOLIO 데이터에 덮어씌운다.
# 라이브 fetch가 안 되는 환경(오프라인 등)에서는 data/portfolio_overrides.csv 스냅샷으로 폴백한다.
# ---------------------------------------------------------------------------
PORTFOLIO_SHEET_ID = "1CBm1gLCxbn_YemTOhjkqna_pg5_aJiFe"
PORTFOLIO_SHEET_CSV_URL = f"https://docs.google.com/spreadsheets/d/{PORTFOLIO_SHEET_ID}/export?format=csv"
PORTFOLIO_SHEET_LOCAL_FALLBACK = os.path.join(ROOT, "data", "portfolio_overrides.csv")

# 로고 파일을 직접 전달받아 사이트 assets에 올려둔 것들 (구글 드라이브 링크는 핫링크가 불안정해서
# 직접 받은 파일을 우선 사용한다. 회사명 -> 상대 경로)
LOCAL_LOGO_OVERRIDES = {
    "페이히어": "assets/portfolio/payhere.png",
    "고레로보틱스": "assets/portfolio/gole-robotics.png",
    "티제이랩스": "assets/portfolio/tjlabs.png",
    "알세미": "assets/portfolio/alsemy.png",
    "뉴메스": "assets/portfolio/newmes.png",
    "크래프타": "assets/portfolio/crafta.png",
    "리뉴어스랩": "assets/portfolio/renewearthlab.png",
    "수앤캐롯츠": "assets/portfolio/sooandcarrots.png",
    "매월매주": "assets/portfolio/mewolmejoo.png",
    "매일새옷": "assets/portfolio/maeilsaeot.png",
    "필드멘토": "assets/portfolio/fieldmentor.png",
    "비랩트": "assets/portfolio/berapt.png",
    "비사이드코리아": "assets/portfolio/bside.png",
    "준컴퍼니": "assets/portfolio/joon-company.png",
    "조인트": "assets/portfolio/joint.png",
    "큐팁": "assets/portfolio/cutib.png",
    "론픽": "assets/portfolio/ronfic.png",
    "쿼타랩": "assets/portfolio/quotalab.png",
    "테네터스": "assets/portfolio/tenetus.png",
    "스위그": "assets/portfolio/swyg.png",
    "moAIs": "assets/portfolio/moais.png",
    "모아이즈": "assets/portfolio/moais.png",
    "모아이스": "assets/portfolio/moais.png",
    "마이프차": "assets/portfolio/myfcha.png",
    "MYFCHA": "assets/portfolio/myfcha.png",
    "마이프랜차이즈": "assets/portfolio/myfcha.png",
    "FlareLane": "assets/portfolio/flarelane.svg",
    "플레어레인": "assets/portfolio/flarelane.svg",
    "플레어랩스": "assets/portfolio/flarelane.svg",
    "엑스크루": "assets/portfolio/xcrew.png",
    "브이드림": "assets/portfolio/vdream.png",
    "서사": "assets/portfolio/seosa.png",
    "디지털뉴트리션": "assets/portfolio/digitalnutrition.png",
    "언디파인드": "assets/portfolio/undefined.png",
    "나니아랩스": "assets/portfolio/narnialabs.png",
    "핀스케어": "assets/portfolio/finthcare.png",
    "FinthCare": "assets/portfolio/finthcare.png",
    "유비스랩": "assets/portfolio/ubl-u.png",
    "리조트피플": "assets/portfolio/resortpeople.png",
    "크픽": "assets/portfolio/kpick.svg",
    "같다": "assets/portfolio/gatda.png",
    "남도마켓": "assets/portfolio/namdomarket.png",
    "빅셀글로벌": "assets/portfolio/bigcell.svg",
    "링크루트": "assets/portfolio/linkroute.png",
    "에이아이링고": "assets/portfolio/ailinggo.png",
    "더트라이브": "assets/portfolio/thetrive.png",
    "케이뷰티월드와이드": "assets/portfolio/kbeautyww.png",
    "Argos Identity": "assets/portfolio/argos.png",
    "쏘핏": "assets/portfolio/sofit.png",
    "SOFIT": "assets/portfolio/sofit.png",
    "아르고노트에이아이": "assets/portfolio/argonaut-ai.png",
    "Argonaut AI": "assets/portfolio/argonaut-ai.png",
    "아르고넛 AI": "assets/portfolio/argonaut-ai.png",
}

def _normalize_url(url):
    if not url:
        return ""
    if not re.match(r"^https?://", url, re.I):
        return "https://" + url
    return url

def _drive_direct_image_url(url):
    """구글 드라이브 '보기' 링크를 <img>에서 바로 로드 가능한 직접 이미지 URL로 변환한다.
    파일이 '링크가 있는 모든 사용자'로 공유되어 있어야 실제로 로드된다."""
    m = re.search(r"/d/([a-zA-Z0-9_-]+)", url) or re.search(r"[?&]id=([a-zA-Z0-9_-]+)", url)
    if not m:
        return url
    file_id = m.group(1)
    return f"https://drive.google.com/uc?export=view&id={file_id}"

def _norm_company_name(name):
    s = name or ""
    for tok in ["농업회사법인", "주식회사", "(주)", "(유)"]:
        s = s.replace(tok, "")
    return re.sub(r"\s+", "", s).strip()

def load_portfolio_sheet_rows():
    raw = None
    try:
        req = urllib.request.Request(PORTFOLIO_SHEET_CSV_URL, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            raw = resp.read().decode("utf-8-sig")
        print("portfolio sheet: fetched live from Google Sheets")
    except Exception as e:
        if os.path.exists(PORTFOLIO_SHEET_LOCAL_FALLBACK):
            with open(PORTFOLIO_SHEET_LOCAL_FALLBACK, encoding="utf-8-sig") as f:
                raw = f.read()
            print(f"portfolio sheet: live fetch failed ({e}), using local snapshot fallback")
        else:
            print(f"portfolio sheet: live fetch failed ({e}) and no local fallback found; skipping sync")
            return []
    return list(csv.DictReader(io.StringIO(raw)))

def _clean_company_display_name(raw_name):
    s = (raw_name or "").strip()
    s = re.sub(r"^(농업회사법인\s*|주식회사\s*|\(주\)\s*|\(유\)\s*)+", "", s)
    s = re.sub(r"(\s*주식회사|\s*\(주\)|\s*\(유\))+$", "", s)
    return s.strip()

def load_portfolio_from_sheet_only():
    """포트폴리오 페이지는 이제 구글 시트에 있는 회사만 보여준다 (기존 하드코딩 리스트는 사용 안 함)."""
    rows = load_portfolio_sheet_rows()
    by_key = {}
    for row in rows:
        raw_name = (row.get("회사명") or "").strip()
        if not raw_name:
            continue
        visible = (row.get("노출여부(Y/N)") or row.get("노출여부") or "Y").strip().upper()
        if visible == "N":
            continue
        display_name = _clean_company_display_name(raw_name)
        desc = (row.get("한줄소개") or "").strip()
        link = _normalize_url((row.get("홈페이지 URL") or "").strip())
        sheet_img = (row.get("로고 이미지 URL") or "").strip()
        if display_name in LOCAL_LOGO_OVERRIDES:
            img = LOCAL_LOGO_OVERRIDES[display_name]
        elif sheet_img and "drive.google.com" in sheet_img:
            img = _drive_direct_image_url(sheet_img)
        elif sheet_img:
            img = sheet_img
        else:
            img = ""
        by_key[_norm_company_name(raw_name)] = (display_name, desc, img, link)
    return list(by_key.values())

# ---------------------------------------------------------------------------
# NEWS SHEET SYNC ("뉴스클리핑" 탭 — 별도 스프레드시트)
# ---------------------------------------------------------------------------
NEWS_SHEET_ID = "1AIWDfnG54uY55Rz1tuc6IwHtQm5R5qbqfwrAgLGlqFs"
NEWS_SHEET_TAB = "뉴스클리핑"
NEWS_SHEET_GVIZ_URL = (
    f"https://docs.google.com/spreadsheets/d/{NEWS_SHEET_ID}/gviz/tq?tqx=out:csv&sheet="
    + urllib.parse.quote(NEWS_SHEET_TAB)
)
NEWS_SHEET_LOCAL_FALLBACK = os.path.join(ROOT, "data", "news_clipping.csv")

def load_news_sheet_rows():
    raw = None
    try:
        req = urllib.request.Request(NEWS_SHEET_GVIZ_URL, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            raw = resp.read().decode("utf-8-sig")
        print("news sheet: fetched live from Google Sheets")
    except Exception as e:
        if os.path.exists(NEWS_SHEET_LOCAL_FALLBACK):
            with open(NEWS_SHEET_LOCAL_FALLBACK, encoding="utf-8-sig") as f:
                raw = f.read()
            print(f"news sheet: live fetch failed ({e}), using local snapshot fallback")
        else:
            print(f"news sheet: live fetch failed ({e}) and no local fallback found; skipping sync")
            return []
    return list(csv.DictReader(io.StringIO(raw)))

def load_news_from_sheet():
    rows = load_news_sheet_rows()
    by_link = {}
    for row in rows:
        title_raw = _clean_text(row.get("기사 제목"))
        link = _clean_text(row.get("링크"))
        date_raw = _clean_text(row.get("날짜"))
        company = _clean_text(row.get("회사명"))
        if not title_raw or not link:
            continue
        date_display = date_raw.replace("-", ".") if re.match(r"^\d{4}-\d{2}-\d{2}$", date_raw) else date_raw
        combined_title = f"[{company}] {title_raw}" if company else title_raw
        by_link[link] = (date_raw, date_display, _safe_html_text(combined_title), link)
    items = list(by_link.values())
    items.sort(key=lambda x: x[0], reverse=True)
    return [(date_display, title, link) for _raw, date_display, title, link in items]

LOGO_MARK = '''<img src="assets/brand/kimgisa-mark.png" alt="" class="brand-mark">'''

# Small line-icon illustrations used on card headers (same palette as HERO_ART)
CARD_ICONS = {
    "route": '''<svg viewBox="0 0 24 24" fill="none"><circle cx="6" cy="6" r="2.4" stroke="currentColor" stroke-width="1.7"/><circle cx="18" cy="18" r="2.4" stroke="currentColor" stroke-width="1.7"/><path d="M8 7c3 0 2 6 5 6s2-6 5-6" stroke="currentColor" stroke-width="1.7" stroke-linecap="round"/></svg>''',
    "handshake": '''<svg viewBox="0 0 24 24" fill="none"><path d="M3 12l4-4 4 3 3-3 4 4" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"/><path d="M3 12v4a2 2 0 0 0 2 2h1M21 12v4a2 2 0 0 1-2 2h-1" stroke="currentColor" stroke-width="1.7" stroke-linecap="round"/></svg>''',
    "chart": '''<svg viewBox="0 0 24 24" fill="none"><path d="M4 20V10M11 20V4M18 20v-7" stroke="currentColor" stroke-width="1.9" stroke-linecap="round"/></svg>''',
    "team": '''<svg viewBox="0 0 24 24" fill="none"><circle cx="9" cy="8" r="3" stroke="currentColor" stroke-width="1.7"/><circle cx="17" cy="9.5" r="2.3" stroke="currentColor" stroke-width="1.7"/><path d="M3.5 20c.6-3.4 3-5 5.5-5s4.9 1.6 5.5 5M14.5 20c.4-2.4 1.9-4 4-4.4" stroke="currentColor" stroke-width="1.7" stroke-linecap="round"/></svg>''',
    "money": '''<svg viewBox="0 0 24 24" fill="none"><rect x="3" y="6" width="18" height="12" rx="2" stroke="currentColor" stroke-width="1.7"/><circle cx="12" cy="12" r="2.6" stroke="currentColor" stroke-width="1.7"/></svg>''',
    "network": '''<svg viewBox="0 0 24 24" fill="none"><circle cx="12" cy="5" r="2" stroke="currentColor" stroke-width="1.7"/><circle cx="5" cy="18" r="2" stroke="currentColor" stroke-width="1.7"/><circle cx="19" cy="18" r="2" stroke="currentColor" stroke-width="1.7"/><path d="M12 7v5M12 12l-6 4M12 12l6 4" stroke="currentColor" stroke-width="1.7"/></svg>''',
    "mentor": '''<svg viewBox="0 0 24 24" fill="none"><path d="M4 19V8a2 2 0 0 1 2-2h12a2 2 0 0 1 2 2v7a2 2 0 0 1-2 2H9l-5 3Z" stroke="currentColor" stroke-width="1.7" stroke-linejoin="round"/><path d="M8 9h8M8 12h5" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/></svg>''',
    "flag": '''<svg viewBox="0 0 24 24" fill="none"><path d="M5 21V4M5 4h13l-3 4 3 4H5" stroke="currentColor" stroke-width="1.7" stroke-linejoin="round"/></svg>''',
}

def icon_badge(name):
    return f'<div class="icon-badge">{CARD_ICONS[name]}</div>'

# Decorative "route" illustration used on the homepage hero (right side, desktop only)
HERO_ART = '''<svg class="hero-art" aria-hidden="true" width="520" height="600" viewBox="0 0 520 600" fill="none" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <radialGradient id="heroGlow1" cx="50%" cy="50%" r="50%">
      <stop offset="0%" stop-color="#bfd6ff" stop-opacity="0.55"/>
      <stop offset="100%" stop-color="#bfd6ff" stop-opacity="0"/>
    </radialGradient>
    <radialGradient id="heroGlow2" cx="50%" cy="50%" r="50%">
      <stop offset="0%" stop-color="#dbe9ff" stop-opacity="0.6"/>
      <stop offset="100%" stop-color="#dbe9ff" stop-opacity="0"/>
    </radialGradient>
  </defs>
  <circle cx="360" cy="150" r="140" fill="url(#heroGlow1)"/>
  <circle cx="80" cy="430" r="120" fill="url(#heroGlow2)"/>
  <path d="M20 480 C 120 440, 60 320, 180 280 S 340 220, 300 90" fill="none" stroke="#c9dbfb" stroke-width="3" stroke-dasharray="2 14" stroke-linecap="round"/>
  <circle cx="20" cy="480" r="9" fill="#dce8ff" stroke="#3b9dff" stroke-width="2"/>
  <circle cx="180" cy="280" r="7" fill="#eef3fd" stroke="#3b9dff" stroke-width="2"/>
  <g transform="translate(280,68)">
    <path d="M12 2C7.58 2 4 5.58 4 10c0 5.25 6.5 11.25 7.06 11.76a1.4 1.4 0 0 0 1.88 0C13.5 21.25 20 15.25 20 10c0-4.42-3.58-8-8-8Z" fill="#1d4ed8" transform="scale(1.9)"/>
    <circle cx="12" cy="10" r="3.1" fill="#ffffff" transform="scale(1.9)"/>
  </g>
  <rect x="340" y="290" width="150" height="88" rx="14" fill="#ffffff" stroke="#e4e8f0" stroke-width="1.5"/>
  <circle cx="366" cy="317" r="4" fill="#1d4ed8"/>
  <text x="378" y="321" font-family="Pretendard,sans-serif" font-size="11.5" font-weight="700" fill="#0f1b3d">TIPS 운영사</text>
  <circle cx="366" cy="343" r="4" fill="#8ec8ff"/>
  <text x="378" y="347" font-family="Pretendard,sans-serif" font-size="11.5" font-weight="700" fill="#0f1b3d">EXIT 경험</text>
</svg>'''

NAV_ITEMS = [
    ("index.html", "홈"),
    ("about.html", "소개"),
    ("program.html", "프로그램"),
    ("portfolio.html", "포트폴리오"),
    ("team.html", "팀"),
    ("news.html", "뉴스"),
]

def nav_html(active):
    links = []
    mlinks = []
    for href, label in NAV_ITEMS:
        cls = " active" if href == active else ""
        links.append(f'<a href="{href}" class="nav-link{cls}">{label}</a>')
        mlinks.append(f'<a href="{href}">{label}</a>')
    links_html = "\n        ".join(links)
    mlinks_html = "\n        ".join(mlinks)
    cta_cls = " active" if active == "contact.html" else ""
    return f'''<nav class="nav">
    <div class="wrap">
      <a href="index.html" class="nav-logo">{LOGO_MARK}<span style="color:var(--text);font-weight:800;">김기사랩</span><span>KIMGISA LAB</span></a>
      <div class="nav-links">
        {links_html}
      </div>
      <a href="contact.html" class="nav-cta{cta_cls}">투자 검토 요청 ↗</a>
      <button class="nav-toggle" aria-label="메뉴 열기" aria-expanded="false">
        <svg width="26" height="26" viewBox="0 0 24 24" fill="none"><path d="M3 6h18M3 12h18M3 18h18" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>
      </button>
    </div>
  </nav>
  <div class="nav-mobile">
    <div class="wrap">
      {mlinks_html}
      <a href="contact.html" class="btn btn-primary nav-cta">투자 검토 요청 ↗</a>
    </div>
  </div>'''

FOOTER_HTML = f'''<footer>
    <div class="wrap">
      <div class="footer-top">
        <div class="footer-col">
          <div class="footer-brand">{LOGO_MARK}<span>김기사랩 KIMGISA LAB</span></div>
          <p style="max-width:320px;">국민내비 '김기사'를 만든 창업가들이 세운 액셀러레이터. 처음 가는 길을 걷는 스타트업 곁에서, 다음 목적지까지의 최적 경로를 함께 찾습니다.</p>
        </div>
        <div class="footer-col">
          <h5>Company</h5>
          <a href="about.html">소개</a>
          <a href="team.html">팀</a>
          <a href="news.html">뉴스</a>
        </div>
        <div class="footer-col">
          <h5>Program</h5>
          <a href="program.html">투자 프로그램</a>
          <a href="portfolio.html">포트폴리오</a>
          <a href="contact.html">투자 검토 요청</a>
        </div>
        <div class="footer-col">
          <h5>Contact</h5>
          <p>서울시 용산구 한강대로 145, 202호</p>
          <a href="mailto:IR@kimgisacompany.com">IR@kimgisacompany.com</a>
        </div>
      </div>
      <div class="footer-bottom">
        <span>© 2026 KIMGISA LAB. All rights reserved.</span>
        <span>액셀러레이터 김기사랩</span>
      </div>
    </div>
  </footer>'''

def page(title, description, active, body, extra_head=""):
    nav = nav_html(active)
    return f'''<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title} | 김기사랩 KIMGISA LAB</title>
<meta name="description" content="{description}">
<link rel="icon" href="assets/brand/favicon.png" type="image/png">
<link rel="stylesheet" as="style" crossorigin href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.css">
<link rel="stylesheet" href="assets/style.css">
{extra_head}
</head>
<body>
<div class="top-bar"></div>
<div class="route-bg"></div>
{nav}
{body}
{FOOTER_HTML}
<script src="assets/script.js"></script>
</body>
</html>'''

def write(name, html):
    with open(os.path.join(ROOT, name), "w", encoding="utf-8") as f:
        f.write(html)
    print("wrote", name)

# ---------------------------------------------------------------------------
# DATA
# ---------------------------------------------------------------------------

FOUNDERS = [
    {
        "name": "신명진",
        "role": "김기사랩 대표",
        "img": "assets/team/shinmj.jpg",
    },
    {
        "name": "박종환",
        "role": "김기사랩 파트너",
        "img": "assets/team/parkjh2.jpg",
    },
    {
        "name": "김원태",
        "role": "김기사랩 파트너",
        "img": "assets/team/kimwt.jpg",
    },
]

TEAM_MEMBERS = [
    {"name": "박현선", "role": "이사", "img": "assets/team/parkhs2.jpg"},
    {"name": "이수진", "role": "팀장", "img": "assets/team/leesj2.jpg"},
    {"name": "김동욱", "role": "실리콘밸리 파트너", "img": "assets/team/kimdw.png"},
]

NETWORK = {
    "투자사": [
        ("뮤렉스파트너스", "이범석 대표"),
        ("라구나인베스트먼트", "박영호 대표"),
        ("AG인베스트먼트", "이범준 대표"),
        ("에이티넘인베스트먼트", "박상호 전무"),
        ("한국투자엑셀러레이터", "이탁림 실장"),
    ],
    "전문가": [
        ("야나두", "김민철 대표"),
        ("넵튠", "강율빈 대표"),
        ("올거나이즈", "이창수 대표"),
        ("아라네트워크", "김상혁 대표"),
        ("두나무", "이석우 대표"),
    ],
    "업무제휴": [
        ("서울경제진흥원", ""),
        ("서울창업허브", ""),
        ("법무법인 비트", ""),
        ("한국앤젤투자협회", ""),
        ("기업보증기금", ""),
    ],
}

PORTFOLIO = [
    ("테네터스", "VR·AI 기반 신경과/안과 검사·진단 SW 의료기기", "https://static.wixstatic.com/media/58c43b_8a809eda771a4562816751a2df419341~mv2.jpg"),
    ("브이드림", "기업 장애인 인사관리 플랫폼", "https://static.wixstatic.com/media/9e8cfc_ab820697cb874e6db0d76c33c057f9c9~mv2.png"),
    ("티라움", "공간 플래너 앱 '꾸보'", "https://static.wixstatic.com/media/b5bf9e_a4510abdda594ca9969f0536f8d4ba12~mv2_d_1372_1756_s_2.png"),
    ("빅쏠", "카드 혜택 통합 관리 앱 '더쎈카드'", "https://static.wixstatic.com/media/b5bf9e_89ae1a7d40fe494594f0b73ad51fc3b4~mv2.png"),
    ("21그램", "반려동물 장례 중개 서비스", "https://static.wixstatic.com/media/b5bf9e_2a8c525e8769482b907f1abb1650c68d~mv2.png"),
    ("위밋모빌리티", "차량 운영·물류 디지털화 솔루션 '루티'", "https://static.wixstatic.com/media/58c43b_b574f8550bae4ceabb6dd5f36838e50c~mv2.png"),
    ("인디펜던트", "피트니스 멤버십 공유 플랫폼 '니짐내짐'", "https://static.wixstatic.com/media/58c43b_0e5d8db4a7b34a5ba423e2130b2bdf48~mv2.png"),
    ("백스테이션", "부동산 경매 전문가 상담·분석 서비스", "https://static.wixstatic.com/media/b5bf9e_5b59744b246340f1a0b4440372e2d256~mv2.jpg"),
    ("어뎁션", "브랜드·사물 본질 연구 기반 디자인 솔루션", "https://static.wixstatic.com/media/b5bf9e_feea6b79ea1c409cb973475cb37e9c38~mv2_d_1761_1761_s_2.png"),
    ("더트라이브", "프리미엄 자동차 구독 서비스", "https://static.wixstatic.com/media/9e8cfc_c12dded4423044f38cf3f3a18a47c5a5~mv2.png"),
    ("마이프랜차이즈", "No.1 프랜차이즈 창업 정보 플랫폼", "https://static.wixstatic.com/media/58c43b_ffcc881af7c647f2852fd5e997a52fe8~mv2.png"),
    ("페이히어", "클라우드 기반 모바일 POS", "https://static.wixstatic.com/media/b5bf9e_08cc30fade45410da2e3c1790df7fb3b~mv2.jpg"),
    ("쿼타랩", "기업 캡테이블 관리 플랫폼 '쿼타북'", "https://static.wixstatic.com/media/58c43b_31720e6700844bbab500f45c1b359e00~mv2.png"),
    ("닫닫닫", "웹툰·툰 영상 제작 플랫폼", "https://static.wixstatic.com/media/58c43b_1988d00ea8904249afefafad1c9d652a~mv2.jpeg"),
    ("모히또게임즈", "모바일 게임 제작 스튜디오", "https://static.wixstatic.com/media/58c43b_7f2b82d2144249459e672375a9e82642~mv2.webp"),
    ("같다", "폐기물·중고제품 모바일 수거 서비스 '빼기'", "https://static.wixstatic.com/media/b5bf9e_a085f6b51d5345c18cec0c147cf0c5b1~mv2.jpg"),
    ("언디파인드", "아마추어 이스포츠 리그 운영 플랫폼", "https://static.wixstatic.com/media/b5bf9e_d3978829be024760ba2d984d9ada7879~mv2.png"),
    ("클로넷", "숏클립 영상 컨텐츠 커머스", "https://static.wixstatic.com/media/b5bf9e_1e0c89fa81db4000b420048b3a511571~mv2.jpg"),
    ("알세미", "AI 기반 반도체 모델링·시뮬레이션(EDA)", "https://static.wixstatic.com/media/9e8cfc_f06244571526498e9807d4f2952240fa~mv2.png"),
    ("태거스", "이커머스 원스톱 마케팅 솔루션", "https://static.wixstatic.com/media/9e8cfc_ac9be2f27038494ba8ef63eed87540d5~mv2.png"),
    ("하이브", "글로벌 소셜 어학 플랫폼 'Hibee'", "https://static.wixstatic.com/media/b5bf9e_576750c7b99746f3bb6a2c67fc815265~mv2.jpg"),
    ("크래프타", "온라인 주문서 플랫폼 'TMM'", "https://static.wixstatic.com/media/b5bf9e_4f040e55fa514845b0946b55d2cca2e4~mv2.png"),
    ("디네이쳐", "희소 약리활성물질 대량추출 기반 신약개발", "https://static.wixstatic.com/media/5ca4aa_518a488ecd2840ec8d21d01a83041061~mv2.png"),
    ("유비스랩", "축구 분석 웨어러블 솔루션", "https://static.wixstatic.com/media/5ca4aa_55c2a335c03342ed872cbb37588bbfa1~mv2.png"),
    ("오늘의픽업", "새벽·당일배송 프리미엄 물류 플랫폼", "https://static.wixstatic.com/media/9e8cfc_c26890826c3b4df6ab1c1c1de9ecf964~mv2.png"),
    ("모아이스", "AI 골프 코치 서비스 '골프픽스'", "https://static.wixstatic.com/media/b5bf9e_8727d1a801ad428584816fce2f7d37bd~mv2.jpg"),
    ("숫자쏭컴퍼니", "전 연령 타깃 캐릭터·콘텐츠 IP 제작", "https://static.wixstatic.com/media/b5bf9e_b0c32ea43c3e40a19302ec8059be47b5~mv2.jpeg"),
    ("빌리어네어즈", "소셜 투자 서비스 '더리치'", "https://static.wixstatic.com/media/b5bf9e_5c71a75d38a14cafa535a193d910b8f7~mv2.png"),
    ("티제이랩스", "실내 위치 솔루션 SCCP", "https://static.wixstatic.com/media/b5bf9e_e3f55c6d2cb14fe4a4dddcc1d8127cea~mv2.png"),
    ("론픽", "데이터 기반 오토헬스 트레이닝 시스템", "https://static.wixstatic.com/media/58c43b_01924f49a757445484f89fca112e7ebc~mv2.png"),
    ("퍼플러스", "키즈 크리에이티브 화장품 브랜드 플랫폼", "https://static.wixstatic.com/media/9e8cfc_7121c64e094a419da1e2507043122bc4~mv2.png"),
    ("루미글루", "감성 AI 비서 'Saï'", "https://static.wixstatic.com/media/7e4bce_de21de7746424a779323937cd392da6b~mv2.jpg"),
    ("마요코퍼레이션", "생산자-셀러 매칭 공동구매 플랫폼 '마요'", "https://static.wixstatic.com/media/9e8cfc_a5ed69976b0a4249b6c6638afcf67238~mv2.png"),
    ("굳갱랩스", "3D 아바타 실시간 커뮤니케이션 '키키타운'", "https://static.wixstatic.com/media/58c43b_4b63d8bfbd784e449f748823d9352d95~mv2.png"),
    ("서사", "성인 독서·스피치 콘텐츠 플랫폼", "https://static.wixstatic.com/media/9e8cfc_8360ec57a2be495c9d222b15e66f8810~mv2.png"),
    ("레이첼블루", "지속가능 소비 커머스 플랫폼", "https://static.wixstatic.com/media/9e8cfc_4376882e773c4853949c33b6ab4b15eb~mv2.jpg"),
    ("딜리버스", "머신러닝 기반 소형화물 배송 플랫폼", "https://static.wixstatic.com/media/58c43b_99d29b56af8b423b85325ff690698af5~mv2.png"),
    ("리조트피플", "건강한 라이프스타일 커뮤니티 플랫폼", "https://static.wixstatic.com/media/9e8cfc_7faeccae763347e7b9108e3401af37f9~mv2.png"),
    ("클리카", "Auto TinyML SaaS 플랫폼", "https://static.wixstatic.com/media/58c43b_90a268edcf6742ab8ec87b8959e5a4dd~mv2.png"),
    ("비사이드코리아", "주주 인증·행동주의 캠페인 플랫폼", "https://static.wixstatic.com/media/58c43b_9560163ff6c147de8ced0508a3439202~mv2.png"),
    ("D.TO", "AI 기반 AEC 디자인 협업 플랫폼", "https://static.wixstatic.com/media/58c43b_22270867fa9549d3a1b94b45f0b55b8c~mv2.png"),
    ("CEEYA", "상호협력 기반 커리어 성장 플랫폼", "https://static.wixstatic.com/media/58c43b_b8130743edda438bad01bfd33bfcf841~mv2.jpg"),
    ("쏘핏", "여성 스포츠웨어·언더웨어 큐레이션", "https://static.wixstatic.com/media/58c43b_95a9d3c362a34852835ef5d82fda40af~mv2.png"),
    ("오렌지풋볼네트워크", "글로벌 스포츠 교육 콘텐츠 플랫폼 'OFN'", "https://static.wixstatic.com/media/58c43b_e0ff39787ddd4c148471d73d2c36a85c~mv2.png"),
    ("비랩트", "작가 응원 커뮤니티 서비스 '숄더'", "https://static.wixstatic.com/media/58c43b_ef688d54002a44c0abfbd1f4d2cb98a9~mv2.jpg"),
    ("엑스크루", "검증된 크루 기반 액티비티 플랫폼", "https://static.wixstatic.com/media/58c43b_3a41cf318d54467bac82b4dacafc4127~mv2.png"),
    ("준컴퍼니", "비대면 신차 비교견적 앱 '카랩'", "https://static.wixstatic.com/media/58c43b_633b1931f62543e6b17b53881205de2f~mv2.png"),
    ("필드멘토", "프로골퍼 섭외·레슨 매칭 플랫폼", "https://static.wixstatic.com/media/58c43b_c9a1369ff9f54301bbc7f0b827d89235~mv2.png"),
    ("고레로보틱스", "건설현장 자율주행 자재배송 로봇", "https://static.wixstatic.com/media/58c43b_0a22a769dea645c88857a2fda65e3084~mv2.jpg"),
    ("케이뷰티월드와이드", "베트남 로컬 뷰티 브랜드 엑셀러레이터", "https://static.wixstatic.com/media/58c43b_9d82f63ef1c148638cae414f7ade1773~mv2.jpg"),
    ("나니아랩스", "생성형 AI 기반 제품 설계·디자인 솔루션", "https://static.wixstatic.com/media/58c43b_180d10dc577349e494717740cfa1510f~mv2.png"),
    ("Argos Identity", "비대면 신원 확인 온보딩 솔루션", "https://static.wixstatic.com/media/58c43b_0eef0badac0b44d28544df78c590fdc1~mv2.png"),
    ("매월매주", "국내 최초 IP 기반 주류 브랜딩 서비스", "https://static.wixstatic.com/media/58c43b_2b07ba7788224ff381bb1485a3c770c7~mv2.png"),
    ("디지털뉴트리션", "의학적 근거 기반 정신건강 사운드 솔루션", "https://static.wixstatic.com/media/58c43b_28eb625763434fefb297d2558007eb11~mv2.png"),
    ("세컨드유레카", "프랜차이즈 빌더 플랫폼 & FAPP", "https://static.wixstatic.com/media/58c43b_890023d022c94e509b915212496d1a3a~mv2.jpg"),
    ("빅셀글로벌", "온라인 쇼핑몰 통합관리 시스템 'BIGCell'", "https://static.wixstatic.com/media/58c43b_f58c605b26584e148c29cdbdb6dd5790~mv2.jpg"),
    ("스위그", "AI 기반 개발 프로젝트 관리 툴 'Riido'", "https://static.wixstatic.com/media/58c43b_7b226b4dc1214b76b030b91dfe57885b~mv2.png"),
    ("뉴메스", "초경량 LMM 온톨로지 솔루션", "https://static.wixstatic.com/media/58c43b_fc2ba6a5cb9047698f332d0903c893f5~mv2.png"),
    ("에이아이링고", "로펌·기업용 AI 법률 번역 솔루션", "https://static.wixstatic.com/media/58c43b_d6cf95f2dad44de7ad81c53552a0f533~mv2.jpg"),
    ("남도마켓", "K도매 생산자 컨시어지 거래 플랫폼", "https://static.wixstatic.com/media/58c43b_d1f8cfd9926c465a90f22cd147a74e84~mv2.png"),
    ("핀스케어", "기업 회원 전용 병원 예약 서비스", "https://static.wixstatic.com/media/7e4bce_65d998c96b454af48f6bfb2a183d3ef3~mv2.png"),
    ("아르고노트에이아이", "SAT 시장 겨냥 AI 튜터", "https://static.wixstatic.com/media/7e4bce_6807c3b39ea74c9586c0c502278d2b1e~mv2.png"),
    ("매일새옷", "세탁업 DX 기반 문 앞 세탁 서비스", "https://static.wixstatic.com/media/7e4bce_c918a700b07f4e888e92d0a47de96367~mv2.png"),
]

# lookup for reusing existing (name -> (desc, img)) from the flat PORTFOLIO list above
_PF_LOOKUP = {name: (desc, img) for name, desc, img in PORTFOLIO}
_PF_LOOKUP["디네이처"] = _PF_LOOKUP.get("디네이쳐", ("", ""))
_PF_LOOKUP["위밋"] = _PF_LOOKUP.get("위밋모빌리티", ("", ""))
_PF_LOOKUP["Ceeya"] = _PF_LOOKUP.get("CEEYA", ("", ""))
_PF_LOOKUP["ARGOS"] = _PF_LOOKUP.get("Argos Identity", ("", ""))
_PF_LOOKUP["안가본길"] = ("인테리어 역경매 플랫폼 '하우스핏'", "")
_PF_LOOKUP["수앤캐롯츠"] = ("외국인 거주자 커뮤니티 기반 데이터·AI 운영 인프라", "")

def _pf(name):
    desc, img = _PF_LOOKUP.get(name, ("", ""))
    return (name, desc, img)

PORTFOLIO_BATCHES = [
    ("1기", [_pf(n) for n in ["21그램","더트라이브","마이프랜차이즈","백스테이션","브이드림","빅쏠","어뎁션","웰바이","위밋","인디펜던트","테네터스","티라움"]]),
    ("2기", [_pf(n) for n in ["오늘의픽업","유비스랩","같다","닫닫닫","디네이처","모히또게임즈","안가본길","쿼타랩","알세미","인디펜던트","오몰래","클로넷","태거스","페이히어","하이브"]]),
    ("3기", [_pf(n) for n in ["론픽","모아이스","브리즈랩","빌리어네어즈","크래프타","티제이랩스","퍼플러스","숫자쏭컴퍼니"]]),
    ("4기", [_pf(n) for n in ["딜리버스","레이첼블루","루미글루","리조트피플","마요코퍼레이션","서사","클리카","풀랩","Ceeya","D.TO","굳갱랩스"]]),
    ("5기", [_pf(n) for n in ["나니아랩스","비랩트","비사이드코리아","쏘핏","오렌지풋볼네트워크","준컴퍼니","필드멘토","엑스크루"]]),
    ("6기", [_pf(n) for n in ["케이뷰티월드와이드","심플컴퍼니","고레로보틱스","ARGOS","세컨드유레카","매월매주","디지털뉴트리션","빅셀글로벌"]]),
    ("7기", [_pf(n) for n in ["에이아이링고","뉴메스","스위그","남도마켓","핀스케어","매일새옷","아르고노트에이아이"]]),
    ("8기", [_pf(n) for n in ["링크루트","리뉴어스랩","물랑드서울","수앤캐롯츠","큐팁","플레어랩스","조인트"]]),
]
PORTFOLIO_TOTAL = sum(len(v) for _, v in PORTFOLIO_BATCHES)

EXIT_CASES = [
    ("BIGSOL (빅쏠)", "2019.04 (1기) 투자 → 2021.07 회수", "M&A (세틀뱅크)", "4.8배"),
    ("오늘의픽업", "2020.11 (2기) 투자 → 2021.12 회수", "M&A (카카오모빌리티)", "4.5배"),
    ("Wemeet Mobility (위밋모빌리티)", "2020.06 (1기) 투자 → 2025.02 회수", "구주 판매", "20배"),
]

PERFORMANCE_CASES = [
    ("DREAM (브이드림)", "장애인 특화 재택근무 시스템 운영", "2019.06 (1기)", "약 80억원"),
    ("payhere (페이히어)", "클라우드 기반 POS 서비스", "2020.06 (2기)", "약 500억원"),
    ("마이프차 (마이프랜차이즈)", "프랜차이즈 창업 플랫폼", "2019.11 (1기)", "약 120억원"),
    ("ronfic (론픽)", "로봇 운동 관리 시스템", "2021.03 (3기)", "약 100억원"),
    ("Delivus (딜리버스)", "AI 기반 당일 도착 택배 서비스", "2022.07 (4기)", "약 200억원"),
    ("GOLE Robotics (고레로보틱스)", "자율주행 건설 로봇 개발", "2023.09 (6기)", "약 57억원"),
]

BATCH_TIMELINE = [
    ("2019", "김기사랩 1기 엑셀러레이팅 (12개사)"),
    ("2020", "김기사랩 2기 엑셀러레이팅 (13개사)"),
    ("2021", "김기사랩 3기 엑셀러레이팅 (13개사)"),
    ("2022", "김기사랩 4기 엑셀러레이팅 (13개사)"),
    ("2023", "김기사랩 5기 엑셀러레이팅 (8개사)"),
    ("2024", "김기사랩 6기 엑셀러레이팅 (8개사)"),
    ("2025", "김기사랩 7기 엑셀러레이팅 (7개사)"),
    ("2026", "김기사랩 8기 엑셀러레이팅 (8개사)"),
]

SOURCING = [
    ("정기 모집", ["매년 1차례 정기 프로그램을 통한 모집", "보도자료, SNS 홍보를 통한 공고 진행", "서류 및 대면 인터뷰를 통해 최종 선발"]),
    ("네트워크를 통한 모집", ["AC/VC 네트워크로부터 추천 접수", "협력 기업, 기투자사로부터 추천 접수", "자료 분석 및 대면 실사를 통해 선발"]),
    ("수시 모집", ["홈페이지를 통한 24/7 상시 접수", "구성원의 오프라인 활동을 통한 발굴", "자료 분석 및 대면 실사를 통해 선발"]),
]

NEWS = [
    ("2022.07.14", "한경닷컴 (긱스)", "국민 앱 '김기사' 만든 3인방...그들의 후배 양성 비법", "https://www.hankyung.com/it/article/202207122276i"),
    ("2021.10.06", "매일경제", "김기사컴퍼니 대표, '국민 내비' 매각 뒤 스타트업 후배 양성 도전", "https://www.mk.co.kr/news/business/view/2021/10/947410/"),
    ("2021.09.08", "디지털투데이", "피트니스 머신 스타트업 '론픽', 팁스 프로그램 선정", "https://www.digitaltoday.co.kr/news/articleView.html?idxno=416494"),
    ("2021.08.17", "한경닷컴 게임톡", "차세대 메타버스 플랫폼 '닫닫닫' 27억원 투자 유치", "https://gametoc.hankyung.com/news/articleView.html?idxno=62266"),
    ("2021.07.15", "플래텀", "'더리치' 운영사 빌리어네어즈, 중기부 팁스 프로그램 선정", "https://platum.kr/archives/166887"),
    ("2021.05.03", "로봇신문", "스마트 헬스케어 스타트업 '론픽', 프리시리즈A 투자유치", "http://m.irobotnews.com/news/articleView.html?idxno=24780"),
    ("2020.11.26", "플래텀", "마이프랜차이즈, 30억 원 시리즈A 투자 유치", "https://platum.kr/archives/153284"),
    ("2020.06.01", "스타트업투데이", "증권 관리 플랫폼 '쿼타북', 프리 시리즈A 투자 유치", "https://www.startuptoday.kr/news/articleView.html?idxno=29985"),
    ("2019.02.26", "플래텀", "김기사 창업자 3인방, 스타트업 발굴 및 투자 나서 — 김기사랩 설립", "https://platum.kr/archives/116823"),
]

# ---------------------------------------------------------------------------
# SHARED FRAGMENTS
# ---------------------------------------------------------------------------

def founder_cards(items=None):
    items = items if items is not None else FOUNDERS
    cells = []
    for f in items:
        cells.append(f'''<div class="founder-card reveal">
          <div class="founder-photo"><img src="{f['img']}" alt="{f['name']}" loading="lazy"></div>
          <div class="founder-body">
            <div class="fname">{f['name']}</div>
            <div class="frole">{f['role']}</div>
          </div>
        </div>''')
    return "\n        ".join(cells)

def network_cards():
    cols = []
    for cat, entries in NETWORK.items():
        rows = []
        for name, role in entries:
            sub = f'<div class="net-role">{role}</div>' if role else ""
            rows.append(f'<div class="net-row"><div class="net-name">{name}</div>{sub}</div>')
        cols.append(f'''<div class="net-col reveal">
          <div class="net-cat">{cat}</div>
          {"".join(rows)}
        </div>''')
    return "\n        ".join(cols)

def portfolio_cards(items=None):
    items = items or PORTFOLIO
    cells = []
    for row in items:
        if len(row) == 4:
            name, desc, img, link = row
        else:
            name, desc, img = row
            link = ""
        tag = "a" if link else "div"
        attrs = f' href="{link}" target="_blank" rel="noopener"' if link else ""
        if img:
            info = f'<div class="info"><div class="pname">{name}</div><div class="pdesc">{desc}</div></div>' if desc else f'<div class="info"><div class="pname">{name}</div></div>'
            cells.append(f'''<{tag} class="pf-card reveal"{attrs}>
          <div class="logo-wrap"><img src="{img}" alt="{name}" loading="lazy"></div>
          {info}
        </{tag}>''')
        else:
            cells.append(f'''<{tag} class="pf-card no-logo reveal"{attrs}>
          <div class="pname-only">{name}</div>
        </{tag}>''')
    return "\n        ".join(cells)

def portfolio_by_batch():
    blocks = []
    for label, items in PORTFOLIO_BATCHES:
        blocks.append(f'''<div class="pf-batch-head reveal"><span class="bnum">{label}</span><span class="blabel">KIMGISA LAB BATCH {label}</span></div>
        <div class="pf-grid">
          {portfolio_cards(items)}
        </div>''')
    return "\n        ".join(blocks)

def exit_case_cards():
    cells = []
    for name, dates, method, mult in EXIT_CASES:
        cells.append(f'''<div class="case-card reveal">
          <div class="cname">{name}</div>
          <div class="crow"><span class="k">투자·회수</span><span class="v">{dates}</span></div>
          <div class="crow"><span class="k">회수 방법</span><span class="v">{method}</span></div>
          <div class="multiple">{mult}<span>Multiple</span></div>
        </div>''')
    return "\n        ".join(cells)

def performance_case_cards():
    cells = []
    for name, desc, dates, amount in PERFORMANCE_CASES:
        cells.append(f'''<div class="case-card reveal">
          <div class="cname">{name}</div>
          <div class="crow"><span class="k">사업 영역</span><span class="v">{desc}</span></div>
          <div class="crow"><span class="k">투자 시기</span><span class="v">{dates}</span></div>
          <div class="multiple" style="font-size:19px;">{amount}<span>후속 투자 유치</span></div>
        </div>''')
    return "\n        ".join(cells)

def batch_timeline():
    items = []
    for year, desc in BATCH_TIMELINE:
        items.append(f'''<div class="timeline-item">
          <div class="year">{year}</div>
          <div class="desc"><p>{desc}</p></div>
        </div>''')
    return "\n        ".join(items)

def sourcing_cards():
    cells = []
    for title, bullets in SOURCING:
        lis = "".join(f'<p style="color:var(--text-dim);font-size:14px;margin-top:8px;">· {b}</p>' for b in bullets)
        cells.append(f'''<div class="info-card reveal">
          <h5>{title}</h5>
          {lis}
        </div>''')
    return "\n        ".join(cells)

NEWS_PAGE_SIZE = 10

def news_rows(items=None):
    items = items if items is not None else NEWS
    rows = []
    for i, (date, title, url) in enumerate(items):
        page = i // NEWS_PAGE_SIZE + 1
        rows.append(f'''<a class="news-item reveal" data-page="{page}" href="{url}" target="_blank" rel="noopener">
          <div class="ndate">{date}</div>
          <div class="ntitle">{title}</div>
          <div class="narrow">↗</div>
        </a>''')
    return "\n        ".join(rows)

def news_pagination(items=None):
    items = items if items is not None else NEWS
    total_pages = max(1, (len(items) + NEWS_PAGE_SIZE - 1) // NEWS_PAGE_SIZE)
    if total_pages <= 1:
        return ""
    buttons = "\n          ".join(
        f'<button class="page-btn{" active" if p == 1 else ""}" data-page="{p}">{p}</button>'
        for p in range(1, total_pages + 1)
    )
    return f'''<div class="pagination" data-total-pages="{total_pages}">
          {buttons}
        </div>'''

# ---------------------------------------------------------------------------
# PAGE: INDEX
# ---------------------------------------------------------------------------

INDEX_BODY = f'''
<section class="hero" style="min-height:86vh;display:flex;align-items:center;padding-top:100px;padding-bottom:100px;">
  <div class="wrap hero-flex">
    <div class="hero-text">
      <div class="hero-badge reveal">📍 <b>SINCE 2018</b>&nbsp; 스타트업 액셀러레이터 김기사랩</div>
      <h1 class="reveal">처음 가는 길엔,<br><span class="accent">내비게이션</span>이 필요합니다.</h1>
      <p class="lead reveal">국민내비 '김기사'를 만든 창업가들이 세운 액셀러레이터, 김기사랩.<br>창업 초기 가장 막막한 순간 가장 필요한 도움을, 실전에서 검증된 경험으로 전합니다.</p>
      <div class="hero-actions reveal">
        <a href="contact.html" class="btn btn-primary">투자 검토 요청 ↗</a>
        <a href="portfolio.html" class="btn btn-ghost">포트폴리오 보기</a>
      </div>
      <div class="hero-partners reveal">
        <div class="label">Partner &amp; Certification</div>
        <div class="badge-row">
          <span class="pill">TIPS 운영사 (일반·딥테크)</span>
          <span class="pill">기보엔젤파트너스</span>
          <span class="pill">분야 제한 없는 투자</span>
        </div>
      </div>
    </div>
    {HERO_ART}
  </div>
</section>
'''

# ---------------------------------------------------------------------------
# PAGE: ABOUT
# ---------------------------------------------------------------------------

ABOUT_BODY = f'''
<section class="page-header">
  <div class="wrap">
    <div class="eyebrow reveal">About Kimgisa Lab</div>
    <h1 class="reveal">세상을 변화시킬 스타트업을 위해,<br>성공을 향한 가장 최적의 길로 이끄는<br>스타트업의 내비게이터가 되겠습니다.</h1>
  </div>
</section>

<section class="section-tight">
  <div class="wrap">
    <div class="eyebrow reveal">The Story</div>
    <h2 class="h-lg reveal">위치기반 서비스로 시작해,<br>국민내비 '김기사'를 만들고, 다시 내비게이터가 되기까지</h2>
    <div class="story-copy" style="margin-top:28px;max-width:760px;">
      <p class="reveal">김기사랩 파트너들의 여정은 2000년, 위치기반 서비스 소프트웨어 개발사 <strong>(주)포인트아이</strong> 창업 멤버로 합류하며 시작됩니다. 2006년 포인트아이는 코스닥에 상장했고, 이 경험을 바탕으로 2010년 박종환·김원태·신명진 세 사람은 <strong>(주)록앤올</strong>을 창업합니다.</p>
      <p class="reveal">"왜 스마트폰 전용 차량용 내비게이션은 없을까?"라는 질문에서 출발한 록앤올은 2011년 <strong>'김기사'</strong> 서비스를 출시했고, 출시 1년 만에 가입자 100만 명을 돌파했습니다. 2014년 가입자 1,000만 명을 넘어섰습니다.</p>
      <p class="reveal">2015년, 김기사는 <strong>카카오에 인수</strong>되어 카카오내비로 리브랜딩되었고 2017년 MAU 500만 명을 돌파했습니다. 세 사람은 인수 이후에도 카카오에 합류해 카카오내비 서비스를 직접 이끌었고, 2018년 세 사람은 그동안의 창업·성장·투자유치·EXIT 경험을 후배 창업가들에게 전달하고자 <strong>김기사랩을 설립</strong>했습니다.</p>
    </div>
  </div>
</section>

<section class="section-tight">
  <div class="wrap">
    <div class="eyebrow reveal">Kimgisa's Journey</div>
    <h2 class="h-lg reveal">김기사의 창업 여정</h2>
    <p class="lead reveal" style="margin-top:16px;">스타트업 창업에서 카카오 인수까지, 팀을 만들고 투자받고 성장시키고 EXIT 하는 모든 과정을 직접 겪었습니다.</p>
    <div class="grid-4" style="margin-top:36px;">
      <div class="card reveal">
        {icon_badge("team")}
        <span class="num">팀 빌딩</span>
        <h4>팀 빌딩의 경험</h4>
        <p>초기 멤버 구성부터 조직 문화 설계까지. 어떤 사람을 언제 채용해야 하는지, 스타트업의 성패가 팀에서 결정된다는 것을 배웠습니다.</p>
      </div>
      <div class="card reveal">
        {icon_badge("chart")}
        <span class="num">서비스 성장</span>
        <h4>서비스 성장의 경험</h4>
        <p>가입자 1,000만까지 각 단계마다 다른 이슈가 존재했습니다. 성장 속도에 맞춰 조직과 시스템을 바꾸고, 유저 데이터로 제품 방향을 결정했습니다.</p>
      </div>
      <div class="card reveal">
        {icon_badge("money")}
        <span class="num">투자 유치</span>
        <h4>투자 유치의 경험</h4>
        <p>IR 준비부터 텀싯 협상까지 투자 프로세스 전반을 경험했습니다. 투자자가 실제로 무엇을 보는지, 투자 유치 이후 관계를 어떻게 관리해야 하는지 압니다.</p>
      </div>
      <div class="card reveal">
        {icon_badge("flag")}
        <span class="num">EXIT</span>
        <h4>EXIT의 경험</h4>
        <p>M&amp;A가 이루어지는 전 과정에 직접 참여했습니다. IPO와 M&amp;A 두 경로를 모두 검토했고, 어떤 시점에 어떤 방식의 EXIT을 준비해야 하는지 압니다.</p>
      </div>
    </div>
  </div>
</section>

<section class="section-tight">
  <div class="wrap">
    <div class="eyebrow reveal">Timeline</div>
    <h2 class="h-lg reveal">김기사랩 연혁</h2>
    <p class="lead reveal" style="margin-top:16px;">2019년 TIPS 운영사로 선정된 이후, 매년 배치 프로그램을 통해 꾸준한 투자 활동을 진행하고 있습니다.</p>
    <div class="timeline reveal" style="margin-top:36px;max-width:760px;">
      <div class="timeline-item">
        <div class="year">2000</div>
        <div class="desc"><h4>(주)포인트아이 창업 멤버</h4><p>위치기반 서비스 소프트웨어 개발</p></div>
      </div>
      <div class="timeline-item">
        <div class="year">2006</div>
        <div class="desc"><h4>(주)포인트아이 IPO</h4><p>코스닥(KOSDAQ) 상장</p></div>
      </div>
      <div class="timeline-item">
        <div class="year">2010~2011</div>
        <div class="desc"><h4>(주)록앤올 창업 · '김기사' 출시</h4><p>국민내비 김기사 개발 및 서비스 출시</p></div>
      </div>
      <div class="timeline-item">
        <div class="year">2013~2015</div>
        <div class="desc"><h4>가입자 1,000만 돌파 · 카카오 인수</h4><p>카카오에 M&amp;A, 카카오내비로 리브랜딩</p></div>
      </div>
      <div class="timeline-item">
        <div class="year">2018</div>
        <div class="desc"><h4>(주)김기사랩 설립</h4><p>엑셀러레이터(창업기획자) 등록</p></div>
      </div>
      <div class="timeline-item">
        <div class="year">2019</div>
        <div class="desc"><h4>TIPS 운영사 선정</h4><p>김기사랩투자조합 1호 결성 · 1기 엑셀러레이팅 진행</p></div>
      </div>
      <div class="timeline-item">
        <div class="year">2020~2021</div>
        <div class="desc"><h4>김기사랩투자조합 2호 결성</h4><p>2기·3기 엑셀러레이팅 진행</p></div>
      </div>
      <div class="timeline-item">
        <div class="year">2022~2024</div>
        <div class="desc"><h4>김기사랩투자조합 3호 결성</h4><p>4기·5기·6기 엑셀러레이팅 진행</p></div>
      </div>
      <div class="timeline-item">
        <div class="year">2025~2026</div>
        <div class="desc"><h4>김기사랩투자조합 4호 결성</h4><p>7기·8기 엑셀러레이팅 진행</p></div>
      </div>
    </div>
  </div>
</section>

<section class="section section-tight">
  <div class="wrap">
    <div class="eyebrow reveal">Why Kimgisa Lab</div>
    <h2 class="h-lg reveal">김기사랩 가치</h2>
    <p class="lead reveal" style="margin-top:16px;">창업부터 서비스 런칭, 가입자 1천만 돌파 등 직접 스타트업을 성장시켜 온 과정과 성공 경험을 바탕으로 후배 창업자를 물심양면으로 지원합니다.</p>
    <div class="grid-3" style="margin-top:36px;">
      <div class="info-card reveal">
        {icon_badge("handshake")}
        <h5>Empathy</h5>
        <div class="val">스타트업의 창업자를 가장 잘 이해하는 투자자</div>
        <p style="margin-top:10px;color:var(--text-dim);font-size:14.5px;line-height:1.65;">대표 파트너 3인의 연쇄 창업 경험을 바탕으로 실제로 창업팀이 겪고 있는 문제, 고민, 위기에 공감하며 현실적인 솔루션을 제공합니다.</p>
      </div>
      <div class="info-card reveal">
        {icon_badge("flag")}
        <h5>Proven Exit</h5>
        <div class="val">실제 EXIT을 경험한 창업자들로 구성된 투자자</div>
        <p style="margin-top:10px;color:var(--text-dim);font-size:14.5px;line-height:1.65;">IPO, M&amp;A 등의 성공 경험을 바탕으로 성공에 대한 학습의 중요성을 전달하고 방향성에 대해 함께 논의할 수 있습니다.</p>
      </div>
      <div class="info-card reveal">
        {icon_badge("money")}
        <h5>Skin in the Game</h5>
        <div class="val">파트너가 직접 조합에 출자하는 투자자</div>
        <p style="margin-top:10px;color:var(--text-dim);font-size:14.5px;line-height:1.65;">구성원이 직접 출자에 참여하여 조합을 결성하므로, 더욱 자율적이면서도 책임감을 가지고 운용합니다.</p>
      </div>
    </div>
  </div>
</section>

<section class="section">
  <div class="wrap">
    <div class="cta-band reveal">
      <div class="eyebrow" style="justify-content:center;">Get Started</div>
      <h2>김기사랩과 함께 다음 목적지를 향해</h2>
      <p>세상을 바꿀 혁신적인 팀을 찾습니다. 성장을 위한 파트너십이 필요하다면 언제든 문을 두드려주세요.</p>
      <div class="hero-actions">
        <a href="contact.html" class="btn btn-primary">투자 검토 요청 ↗</a>
        <a href="program.html" class="btn btn-ghost">프로그램 보기</a>
      </div>
    </div>
  </div>
</section>
'''

# ---------------------------------------------------------------------------
# PAGE: PROGRAM
# ---------------------------------------------------------------------------

PROGRAM_BODY = f'''
<section class="page-header">
  <div class="wrap">
    <div class="eyebrow reveal">Kimgisa Labs Program</div>
    <h1 class="reveal">잠재력 있는 스타트업을 발굴하고,<br>실질적으로 투자합니다.</h1>
    <p class="lead reveal">투자 분야는 특정 산업에 제한을 두지 않고 모든 분야에 열려 있습니다. 세상을 변화시킬 아이디어와 열정, 진정성을 가진 스타트업을 기다립니다.</p>
  </div>
</section>

<section class="section-tight">
  <div class="wrap">
    <div class="eyebrow reveal">Benefits</div>
    <h2 class="h-lg reveal">김기사랩의 창업팀 지원</h2>
    <div class="grid-2" style="margin-top:40px;">
      <div class="card reveal">
        {icon_badge("money")}
        <span class="num">01 · 직접 투자</span>
        <h4>최대 3억 원, 유연한 투자 텀</h4>
        <p>Seed 단계의 창업팀에 최대 3억 원까지 직접 투자를 진행합니다. 투자금액은 회사의 상황에 맞게 유동적으로 조정됩니다.</p>
      </div>
      <div class="card reveal">
        {icon_badge("chart")}
        <span class="num">02 · 후속 투자</span>
        <h4>성장 단계에 맞춘 후속 투자</h4>
        <p>창업기업의 잠재 가능성과 성장 상황에 따라 후속 투자에도 참여합니다.</p>
      </div>
      <div class="card reveal">
        {icon_badge("network")}
        <span class="num">03 · 후속 투자 연계</span>
        <h4>국내외 AC/VC 네트워크 연결</h4>
        <p>김기사랩이 보유한 국내외 AC/VC 네트워크를 통해 후속 투자를 유치할 수 있는 기회를 연결합니다.</p>
      </div>
      <div class="card reveal">
        {icon_badge("mentor")}
        <span class="num">04 · 창업자 밀착 멘토링</span>
        <h4>김기사 창업자들의 단계별 멘토링</h4>
        <p>창업에서 Exit까지 모든 과정을 경험해 본 김기사 파트너들이 창업팀의 상황과 사업 목적에 맞춘 단계별 밀착 멘토링을 진행합니다.</p>
      </div>
    </div>
  </div>
</section>

<section class="section section-tight">
  <div class="wrap">
    <div class="eyebrow reveal">Batch Program</div>
    <h2 class="h-lg reveal">김기사랩 배치 프로그램</h2>
    <p class="lead reveal" style="margin-top:16px;">2019년 이후 매년 기수제로 배치 프로그램을 진행해오고 있으며, 전문가 강연·네트워킹·멘토링 등을 통해 스타트업을 육성하고 있습니다.</p>
    <div class="timeline reveal" style="margin-top:36px;max-width:760px;">
      {batch_timeline()}
    </div>
    <div style="margin-top:28px;">
      <a href="portfolio.html" class="side-link">포트폴리오 전체보기 →</a>
    </div>
  </div>
</section>

<section class="section section-tight">
  <div class="wrap">
    <div class="eyebrow reveal">Who We Look For</div>
    <h2 class="h-lg reveal">이런 팀을 기다립니다</h2>
    <p class="lead reveal" style="margin-top:18px;">특정 분야에 제한을 두지 않습니다. 세상을 변화시킬 아이디어와 열정, 그리고 진정성을 가진 초기 스타트업이라면 누구든 지원할 수 있습니다. 현재 모집 기수 및 일정은 문의를 통해 안내드립니다.</p>
  </div>
</section>

<section class="section">
  <div class="wrap">
    <div class="cta-band reveal">
      <div class="eyebrow" style="justify-content:center;">Get Started</div>
      <h2>지금, 우리 팀의 다음 단계를 이야기해보세요</h2>
      <p>모집 기수, 지원 절차, 투자 조건이 궁금하다면 IR 문의로 편하게 연락해주세요.</p>
      <div class="hero-actions">
        <a href="contact.html" class="btn btn-primary">투자 검토 요청 ↗</a>
        <a href="portfolio.html" class="btn btn-ghost">포트폴리오 보기</a>
      </div>
    </div>
  </div>
</section>
'''

# ---------------------------------------------------------------------------
# PAGE: PORTFOLIO
# ---------------------------------------------------------------------------

PORTFOLIO_LIVE = load_portfolio_from_sheet_only()

PORTFOLIO_BODY = f'''
<section class="page-header">
  <div class="wrap">
    <div class="eyebrow reveal">Portfolio</div>
    <h1 class="reveal">김기사랩과 함께<br>성장하는 스타트업들</h1>
    <p class="lead reveal">2018년 설립 이후, 분야를 가리지 않고 세상을 바꿀 잠재력에 투자해왔습니다. <span style="white-space:nowrap;">AI·딥테크</span>·서비스·플랫폼 등 다양한 카테고리의 회사에 투자합니다.</p>
  </div>
</section>

<section class="section-tight" style="padding-top:0;">
  <div class="wrap">
    <div class="pf-grid">
      {portfolio_cards(PORTFOLIO_LIVE)}
    </div>
  </div>
</section>

<section class="section">
  <div class="wrap">
    <div class="cta-band reveal">
      <div class="eyebrow" style="justify-content:center;">Get Started</div>
      <h2>다음 포트폴리오가 되어보세요</h2>
      <p>세상을 변화시킬 아이디어가 있다면, 김기사랩이 가장 가까운 동료가 되겠습니다.</p>
      <div class="hero-actions">
        <a href="contact.html" class="btn btn-primary">투자 검토 요청 ↗</a>
        <a href="program.html" class="btn btn-ghost">프로그램 보기</a>
      </div>
    </div>
  </div>
</section>
'''

# ---------------------------------------------------------------------------
# PAGE: TEAM
# ---------------------------------------------------------------------------

TEAM_BODY = f'''
<section class="page-header">
  <div class="wrap">
    <div class="eyebrow reveal">Team</div>
    <h1 class="reveal">창업에서 Exit까지,<br>직접 걸어본 사람들</h1>
    <p class="lead reveal">김기사랩은 창업에서 Exit까지 모든 과정을 실제로 경험해본 파트너들로 구성되어 있으며, 이 외에도 다양한 분야의 성공 창업인들이 멘토로 참여해 스타트업을 지원하고 있습니다.</p>
  </div>
</section>

<section class="section-tight" style="padding-top:0;">
  <div class="wrap">
    <div class="eyebrow reveal">Kimgisa Team</div>
    <div class="founder-grid" style="margin-top:36px;">
      {founder_cards(FOUNDERS + TEAM_MEMBERS[:2])}
    </div>
  </div>
</section>

<section class="section">
  <div class="wrap">
    <div class="cta-band reveal">
      <div class="eyebrow" style="justify-content:center;">Get Started</div>
      <h2>우리 팀과 함께 다음 단계를 그려보세요</h2>
      <p>창업 경험을 직접 겪은 파트너들이, 창업팀의 상황에 맞는 실질적인 도움을 드립니다.</p>
      <div class="hero-actions">
        <a href="contact.html" class="btn btn-primary">투자 검토 요청 ↗</a>
        <a href="about.html" class="btn btn-ghost">회사 소개 보기</a>
      </div>
    </div>
  </div>
</section>
'''

# ---------------------------------------------------------------------------
# PAGE: NEWS
# ---------------------------------------------------------------------------

NEWS_LIVE = load_news_from_sheet()

NEWS_BODY = f'''
<section class="page-header">
  <div class="wrap">
    <div class="eyebrow reveal">News</div>
    <h1 class="reveal">언론이 기록한<br>김기사랩</h1>
    <p class="lead reveal">설립 이후 지금까지, 포트폴리오사의 성장과 김기사랩의 활동을 다룬 주요 보도입니다.</p>
  </div>
</section>

<section class="section-tight" style="padding-top:0;">
  <div class="wrap">
    <div class="news-list">
      {news_rows(NEWS_LIVE)}
    </div>
    {news_pagination(NEWS_LIVE)}
  </div>
</section>

<section class="section">
  <div class="wrap">
    <div class="cta-band reveal">
      <div class="eyebrow" style="justify-content:center;">Get Started</div>
      <h2>다음 소식의 주인공이 되어보세요</h2>
      <p>김기사랩과 함께 성장한 다음 이야기를, 여러분의 팀에서 시작해보세요.</p>
      <div class="hero-actions">
        <a href="contact.html" class="btn btn-primary">투자 검토 요청 ↗</a>
        <a href="portfolio.html" class="btn btn-ghost">포트폴리오 보기</a>
      </div>
    </div>
  </div>
</section>
'''

# ---------------------------------------------------------------------------
# PAGE: CONTACT
# ---------------------------------------------------------------------------

CONTACT_BODY = f'''
<section class="page-header">
  <div class="wrap">
    <div class="eyebrow reveal">Contact</div>
    <h1 class="reveal">투자 검토 요청</h1>
    <p class="lead reveal">김기사랩과 함께 세상을 바꿀 혁신적인 팀을 찾습니다. 성장을 위한 파트너십이 필요한 초기 스타트업은 아래 양식 또는 이메일로 IR 자료를 보내주세요.</p>
  </div>
</section>

<section class="section-tight" style="padding-top:0;">
  <div class="wrap">
    <div class="contact-grid">
      <div>
        <div class="info-card reveal" style="margin-bottom:16px;">
          <h5>이메일</h5>
          <div class="val"><a href="mailto:IR@kimgisacompany.com" style="color:var(--accent);">IR@kimgisacompany.com</a></div>
        </div>
        <div class="info-card reveal" style="margin-bottom:16px;">
          <h5>주소</h5>
          <div class="val" style="font-size:15px;">서울시 용산구 한강대로 145, 202호</div>
        </div>
        <div class="info-card reveal">
          <h5>회신 기간</h5>
          <div class="val" style="font-size:15px;">보내주신 자료는 김기사랩 팀에서 신중히 검토한 후<br><strong style="color:var(--accent);">2주 이내</strong>에 회신드립니다.</div>
        </div>
      </div>
      <form id="ir-form" class="reveal" data-endpoint="{APPS_SCRIPT_URL}">
        <div class="form-group">
          <label>회사명 *</label>
          <input type="text" name="company" required placeholder="예) 김기사랩">
        </div>
        <div class="form-group">
          <label>신청자 성함/직함 *</label>
          <input type="text" name="applicant" required placeholder="예) 홍길동/대표">
        </div>
        <div class="form-group">
          <label>법인 설립 일자 *</label>
          <input type="date" name="founded" required>
        </div>
        <div class="form-group">
          <label>사업 아이템명 *</label>
          <input type="text" name="itemName" required placeholder="예) 김기사랩">
        </div>
        <div class="form-group">
          <label>사업 아이템 요약 *</label>
          <textarea name="itemSummary" required placeholder="어떤 문제를 어떻게 풀고 있는 팀인지 간략히 소개해주세요."></textarea>
        </div>
        <div class="form-group">
          <label>연락처 *</label>
          <input type="tel" name="phone" required placeholder="010-0000-0000">
        </div>
        <div class="form-group">
          <label>이메일 *</label>
          <input type="email" name="email" required placeholder="you@company.com">
        </div>
        <div class="form-group">
          <label>사업계획서 업로드 (PDF) *</label>
          <input type="file" name="pitchFile" accept="application/pdf" required>
        </div>
        <div class="form-group">
          <label>희망 Valuation 및 투자금액 *</label>
          <input type="text" name="valuation" required placeholder="예) Pre 20억 / 2억">
        </div>
        <button type="submit" class="btn btn-primary" style="width:100%;justify-content:center;">제출하기 ↗</button>
        <div class="form-status"></div>
        <p class="form-note">* 제출하신 내용과 사업계획서는 IR@kimgisacompany.com으로 자동 전송됩니다.</p>
      </form>
    </div>
  </div>
</section>
'''

# ---------------------------------------------------------------------------
# WRITE PAGES
# ---------------------------------------------------------------------------

write("index.html", page(
    "홈", "세상을 변화시킬 스타트업을 위해 성공을 향한 가장 최적의 길로 이끄는 스타트업의 내비게이터, 김기사랩입니다.",
    "index.html", INDEX_BODY
))
write("about.html", page(
    "소개", "김기사랩은 국민내비 '김기사' 창업가들의 창업 경험과 성공 노하우를 후배 창업가들에게 전달하는 액셀러레이터입니다.",
    "about.html", ABOUT_BODY
))
write("program.html", page(
    "프로그램", "김기사랩의 SEED 투자, 밀착 멘토링, TIPS 운영사, 기보엔젤파트너스 등 액셀러레이팅 프로그램을 소개합니다.",
    "program.html", PROGRAM_BODY
))
write("portfolio.html", page(
    f"포트폴리오 ({len(PORTFOLIO_LIVE)})", f"김기사랩이 투자한 {len(PORTFOLIO_LIVE)}개 포트폴리오 스타트업을 소개합니다.",
    "portfolio.html", PORTFOLIO_BODY
))
write("team.html", page(
    "팀", "창업에서 Exit까지 모든 과정을 경험한 김기사랩의 공동창업자 3인을 소개합니다.",
    "team.html", TEAM_BODY
))
write("news.html", page(
    "뉴스", "김기사랩과 포트폴리오사의 성장을 다룬 주요 언론 보도입니다.",
    "news.html", NEWS_BODY
))
write("contact.html", page(
    "투자 검토 요청", "김기사랩에 투자 검토를 요청하고 싶은 스타트업은 이메일 또는 문의 양식으로 연락해주세요.",
    "contact.html", CONTACT_BODY
))

print("done")
