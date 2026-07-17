#!/usr/bin/env python3
"""Apply the site-wide quality, crawlability, and trust improvements.

The script is intentionally idempotent so the same rules can be applied to new
learning pages before they are published.
"""

from __future__ import annotations

import ast
import html
import json
import re
from pathlib import Path
from urllib.parse import quote


ROOT = Path(__file__).resolve().parents[1]
BASE_URL = "https://moduhistory.com"
REVIEW_DATE = "2026-07-18"

LEGAL_FILES = {
    "404.html",
    "about.html",
    "contact.html",
    "privacy.html",
    "sources.html",
    "terms.html",
}

GENERIC_EXAM_POINTS = re.compile(
    r"(<h3[^>]*>시험 출제 포인트</h3>\s*<ul[^>]*>)\s*"
    r"<li>핵심 용어의 뜻을 단순 암기가 아니라 시대적 배경과 연결해 파악한다\.</li>\s*"
    r"<li>각 사건의 원인 → 전개 → 결과를 순서대로 정리한다\.</li>\s*"
    r"<li>비슷한 제도와 사건을 비교하여 차이점을 구분한다\.</li>\s*"
    r"<li>자료형 문항에서는 사료의 작성 배경과 핵심 표현을 근거로 판단한다\.</li>\s*"
    r"(</ul>)",
    re.S,
)

COMMON_FOOTER = """<footer id="site-quality-footer" style="margin-top:3rem;border-top:1px solid #e2e8f0;background:#fff;color:#475569">
  <div style="max-width:72rem;margin:0 auto;padding:1.5rem 1rem;text-align:center;font-size:.875rem;line-height:1.8">
    <nav aria-label="사이트 정책" style="display:flex;flex-wrap:wrap;justify-content:center;gap:.5rem 1rem;margin-bottom:.5rem">
      <a href="/about.html">사이트 소개</a><a href="/sources.html">편집·출처 원칙</a><a href="/privacy.html">개인정보처리방침</a><a href="/terms.html">이용·저작권 안내</a><a href="/contact.html">오류 신고·문의</a>
    </nav>
    <p>© 2026 모두의 사탐 · 최종 검토 2026-07-18</p>
  </div>
</footer>"""

EDITORIAL_NOTE = """<aside id="site-editorial-note" aria-label="콘텐츠 편집 정보" style="max-width:72rem;margin:2rem auto 0;padding:1rem;border:1px solid #e2e8f0;border-radius:.75rem;background:#f8fafc;color:#475569;font-size:.875rem;line-height:1.7">
  <strong>콘텐츠 정보</strong> · 작성·검토: 모두의 사탐 편집부 · 교육과정 범위에서 학습용으로 재구성 · <a href="/sources.html" style="text-decoration:underline">편집·출처 원칙</a> · <a href="/contact.html" style="text-decoration:underline">오류 신고</a> · 최종 검토 2026-07-18
</aside>"""

ACCESSIBILITY_SCRIPT = """<script id="hidden-box-accessibility">
document.addEventListener('DOMContentLoaded',()=>document.querySelectorAll('.hidden-box').forEach(el=>{
  el.setAttribute('role','button'); el.setAttribute('tabindex','0');
  el.setAttribute('aria-label','가려진 핵심어 보기');
  el.addEventListener('keydown',event=>{if(event.key==='Enter'||event.key===' '){event.preventDefault();el.click();}});
}));
</script>"""


def canonical_for(relative: Path) -> str:
    posix = relative.as_posix()
    if posix == "index.html":
        return f"{BASE_URL}/"
    if posix == "history/hv1/root_index_with_hv1.html":
        return f"{BASE_URL}/history/hv1/"
    if relative.name == "index.html":
        return f"{BASE_URL}/{quote(relative.parent.as_posix(), safe='/')}/"
    return f"{BASE_URL}/{quote(posix, safe='/')}"


def plain_text(fragment: str) -> str:
    fragment = re.sub(r"<script\b.*?</script>", " ", fragment, flags=re.I | re.S)
    fragment = re.sub(r"<style\b.*?</style>", " ", fragment, flags=re.I | re.S)
    fragment = re.sub(r"<[^>]+>", " ", fragment)
    return re.sub(r"\s+", " ", html.unescape(fragment)).strip()


def page_title(document: str, relative: Path) -> str:
    match = re.search(r"<title[^>]*>(.*?)</title>", document, re.I | re.S)
    if match:
        title = plain_text(match.group(1))
        title = re.sub(r"\s*[|·-]\s*모두의 (?:사탐|한국사|공부)\s*$", "", title)
        if title:
            return title
    match = re.search(r"<h1[^>]*>(.*?)</h1>", document, re.I | re.S)
    return plain_text(match.group(1)) if match else relative.stem


def meta_description(document: str, title: str, relative: Path) -> str:
    h1 = re.search(r"<h1[^>]*>(.*?)</h1>", document, re.I | re.S)
    heading = plain_text(h1.group(1)) if h1 else title
    if relative.name == "index.html":
        return f"{heading}의 학습 자료와 단원별 웹 학습지를 한눈에 찾을 수 있는 모두의 사탐 목차입니다."
    if relative.name in LEGAL_FILES:
        descriptions = {
            "404.html": "요청한 페이지를 찾을 수 없습니다. 모두의 사탐 과목별 학습 자료로 이동해 주세요.",
            "about.html": "모두의 사탐이 제공하는 학습 자료의 목적, 편집 방향, 검토 원칙을 안내합니다.",
            "contact.html": "모두의 사탐 학습 자료의 사실 오류, 오탈자, 링크 문제를 신고하는 방법을 안내합니다.",
            "privacy.html": "모두의 사탐의 쿠키, 광고 서비스, 개인정보 처리 기준을 안내합니다.",
            "sources.html": "모두의 사탐 학습 자료의 작성·검토 기준과 우선 참고하는 공신력 있는 출처를 안내합니다.",
            "terms.html": "모두의 사탐 콘텐츠의 이용 범위, 저작권, 면책 사항을 안내합니다.",
        }
        return descriptions[relative.name]
    return f"{heading}의 핵심 개념, 사건의 흐름, 자주 틀리는 부분과 확인 문제를 제공하는 모두의 사탐 웹 학습지입니다."


def extract_json_array(document: str, variable: str):
    match = re.search(rf"\b(?:const|let|var)\s+{re.escape(variable)}\s*=\s*", document)
    if not match:
        return None
    source = document[match.end():].lstrip()
    try:
        value, _ = json.JSONDecoder().raw_decode(source)
    except (json.JSONDecodeError, TypeError):
        # Older pages use JavaScript object literals with unquoted keys. Extract
        # only the balanced array expression, then parse its literal values.
        if not source.startswith("["):
            return None
        depth = 0
        quote_char = ""
        escaped = False
        end = None
        for index, char in enumerate(source):
            if quote_char:
                if escaped:
                    escaped = False
                elif char == "\\":
                    escaped = True
                elif char == quote_char:
                    quote_char = ""
                continue
            if char in {"'", '"'}:
                quote_char = char
            elif char in "[{":
                depth += 1
            elif char in "]}":
                depth -= 1
                if depth == 0:
                    end = index + 1
                    break
        if end is None:
            return None
        literal = source[:end]
        literal = re.sub(r"([{,]\s*)([A-Za-z_$][\w$]*)\s*:", r"\1'\2':", literal)
        try:
            value = ast.literal_eval(literal)
        except (SyntaxError, ValueError):
            return None
    return value if isinstance(value, list) else None


def static_quiz_markup(items: list[object]) -> str:
    cards: list[str] = []
    for index, raw in enumerate(items, 1):
        if not isinstance(raw, dict) or not (raw.get("question") or raw.get("q")):
            continue
        question = html.escape(str(raw.get("question") or raw.get("q")))
        options = raw.get("options") or raw.get("choices") or []
        option_html = "".join(f"<li>{html.escape(str(option))}</li>" for option in options)
        raw_answer = raw.get("answer", "페이지에서 정답을 확인하세요.")
        if isinstance(raw_answer, int) and 0 <= raw_answer < len(options):
            raw_answer = options[raw_answer]
        answer = html.escape(str(raw_answer))
        explanation = html.escape(str(raw.get("explanation", "")))
        cards.append(
            f'<article data-static-quiz="{index}" style="margin:1rem 0;padding:1rem;border:1px solid #e2e8f0;border-radius:.75rem">'
            f'<p><strong>{index}. {question}</strong></p><ol style="margin:.75rem 0;padding-left:1.5rem">{option_html}</ol>'
            f'<details><summary>정답과 해설 보기</summary><p style="margin-top:.5rem"><strong>정답:</strong> {answer}'
            f'{"<br>" + explanation if explanation else ""}</p></details></article>'
        )
    return "".join(cards)


def add_static_quiz(document: str) -> tuple[str, bool]:
    items = extract_json_array(document, "quizData")
    if not items:
        return document, False
    fallback = static_quiz_markup(items)
    if not fallback:
        return document, False
    pattern = re.compile(
        r"(<div\b(?=[^>]*\bid=(['\"])(?:quiz-container|quizContainer|quiz)\2)[^>]*>)(.*?)(</div>)",
        re.I | re.S,
    )

    def replace(match: re.Match[str]) -> str:
        inner = re.sub(r"<!--.*?-->", "", match.group(3), flags=re.S).strip()
        if inner or "data-static-quiz" in match.group(3):
            return match.group(0)
        id_match = re.search(r"\bid=(['\"])([^'\"]+)\1", match.group(1), re.I)
        container_id = id_match.group(2) if id_match else "quiz-container"
        clear = f"<script data-static-fallback-clear>document.getElementById({json.dumps(container_id)}).replaceChildren();</script>"
        return f"{match.group(1)}{fallback}{match.group(4)}{clear}"

    updated, count = pattern.subn(replace, document, count=1)
    return updated, bool(count and updated != document)


def add_static_story(document: str) -> tuple[str, bool]:
    story = extract_json_array(document, "story")
    if not story:
        return document, False
    paragraphs = []
    for raw in story:
        text = str(raw)
        text = re.sub(
            r"<span\b[^>]*data-text=(['\"])(.*?)\1[^>]*>.*?</span>",
            lambda match: html.escape(html.unescape(match.group(2))),
            text,
            flags=re.I | re.S,
        )
        paragraphs.append(f"<p data-static-story>{plain_text(text)}</p>")
    fallback = "".join(paragraphs)
    pattern = re.compile(r"(<div\b(?=[^>]*\bid=(['\"])storyBox\2)[^>]*>)(.*?)(</div>)", re.I | re.S)

    def replace(match: re.Match[str]) -> str:
        inner = re.sub(r"<!--.*?-->", "", match.group(3), flags=re.S).strip()
        if inner:
            return match.group(0)
        clear = '<script data-static-fallback-clear>document.getElementById("storyBox").replaceChildren();</script>'
        return f"{match.group(1)}{fallback}{match.group(4)}{clear}"

    updated, count = pattern.subn(replace, document, count=1)
    return updated, bool(count and updated != document)


def unique_exam_points(document: str) -> tuple[str, bool]:
    keywords = [plain_text(value) for value in re.findall(r"<span class=['\"]keyword-pill['\"]>(.*?)</span>", document, re.S)]
    if len(keywords) < 4:
        return document, False
    picks = (keywords * 3)[:10]
    items = [
        f"{picks[0]}과(와) {picks[1]}의 뜻을 시대적 배경과 함께 구분한다.",
        f"{picks[2]}, {picks[3]}, {picks[4]}이(가) 이어지는 변화의 흐름을 설명한다.",
        f"{picks[5]}와(과) {picks[6]}의 공통점과 차이점을 자료에서 판별한다.",
        f"사료의 핵심 표현을 근거로 {picks[8]}과(와) {picks[9]}를 구별한다.",
    ]

    def replace(match: re.Match[str]) -> str:
        body = "\n            ".join(f"<li>{html.escape(item)}</li>" for item in items)
        return f"{match.group(1)}\n            {body}\n          {match.group(2)}"

    updated, count = GENERIC_EXAM_POINTS.subn(replace, document, count=1)
    return updated, bool(count)


def head_metadata(document: str, relative: Path) -> str:
    canonical = canonical_for(relative)
    title = page_title(document, relative)
    description = meta_description(document, title, relative)
    robots = "noindex,follow" if relative.name == "404.html" or relative.as_posix() == "history/hv1/root_index_with_hv1.html" else "index,follow"
    kind = "CollectionPage" if relative.name == "index.html" else "LearningResource"
    if relative.name in LEGAL_FILES:
        kind = "WebPage"
    structured = {
        "@context": "https://schema.org",
        "@type": kind,
        "name": title,
        "url": canonical,
        "inLanguage": "ko-KR",
        "isAccessibleForFree": True,
        "dateModified": REVIEW_DATE,
        "publisher": {"@type": "Organization", "name": "모두의 사탐", "url": f"{BASE_URL}/"},
    }
    additions: list[str] = []
    if not re.search(r"<meta\s+name=['\"]description['\"]", document, re.I):
        additions.append(f'<meta name="description" content="{html.escape(description, quote=True)}">')
    if not re.search(r"<meta\s+name=['\"]robots['\"]", document, re.I):
        additions.append(f'<meta name="robots" content="{robots}">')
    if not re.search(r"<link\s+rel=['\"]canonical['\"]", document, re.I):
        additions.append(f'<link rel="canonical" href="{canonical}">')
    if not re.search(r"property=['\"]og:site_name['\"]", document, re.I):
        additions.extend(
            [
                '<meta property="og:site_name" content="모두의 사탐">',
                f'<meta property="og:type" content="{html.escape("website" if relative.name == "index.html" else "article")}">',
                f'<meta property="og:title" content="{html.escape(title, quote=True)}">',
                f'<meta property="og:description" content="{html.escape(description, quote=True)}">',
                f'<meta property="og:url" content="{canonical}">',
            ]
        )
    if 'id="site-structured-data"' not in document:
        additions.append(
            '<script id="site-structured-data" type="application/ld+json">'
            + json.dumps(structured, ensure_ascii=False, separators=(",", ":"))
            + "</script>"
        )
    if not additions:
        return document
    return re.sub(r"</head>", "  " + "\n  ".join(additions) + "\n</head>", document, count=1, flags=re.I)


def common_chrome(document: str, relative: Path) -> str:
    if relative.name != "404.html" and 'id="hidden-box-accessibility"' not in document and "hidden-box" in document:
        document = re.sub(r"</body>", ACCESSIBILITY_SCRIPT + "\n</body>", document, count=1, flags=re.I)
    if 'id="site-quality-footer"' not in document:
        if re.search(r"<footer\b", document, re.I):
            document = re.sub(r"<footer\b.*?</footer>", COMMON_FOOTER, document, count=1, flags=re.I | re.S)
        else:
            document = re.sub(r"</body>", COMMON_FOOTER + "\n</body>", document, count=1, flags=re.I)
    is_learning_page = relative.parts[0] in {"history", "social"} and relative.name != "index.html"
    is_alias = relative.as_posix() == "history/hv1/root_index_with_hv1.html"
    if is_learning_page and not is_alias and 'id="site-editorial-note"' not in document:
        document = document.replace(COMMON_FOOTER, EDITORIAL_NOTE + "\n" + COMMON_FOOTER, 1)
    return document


def improve_file(path: Path) -> dict[str, bool]:
    relative = path.relative_to(ROOT)
    original = path.read_text(encoding="utf-8")
    document = original.replace("\x01", "")
    document = document.replace("모두의 공부", "모두의 사탐").replace("모두의 한국사", "모두의 사탐")
    document = document.replace("교과서 핵심 정리", "핵심 개념 정리").replace("스토리텔링 한국사", "흐름으로 이해하기")
    document = document.replace("은/는", "은(는)").replace("이/가", "이(가)").replace("접근를", "접근을")
    # Several legacy pages opened <head> but entered <body> without closing it.
    if "<head" in document.lower() and "</head>" not in document.lower():
        document = re.sub(r"(<body\b)", r"</head>\n\1", document, count=1, flags=re.I)
    document, exam_points = unique_exam_points(document)
    document, static_quiz = add_static_quiz(document)
    document, static_story = add_static_story(document)
    document = head_metadata(document, relative)
    document = common_chrome(document, relative)
    if document != original:
        path.write_text(document, encoding="utf-8")
    return {
        "changed": document != original,
        "exam_points": exam_points,
        "static_quiz": static_quiz,
        "static_story": static_story,
    }


def sitemap_entries(paths: list[Path]) -> list[str]:
    entries = []
    for path in paths:
        relative = path.relative_to(ROOT)
        if relative.name == "404.html" or relative.as_posix() == "history/hv1/root_index_with_hv1.html":
            continue
        priority = "1.0" if relative.as_posix() == "index.html" else ("0.8" if relative.name == "index.html" else "0.6")
        entries.append(
            "  <url>\n"
            f"    <loc>{html.escape(canonical_for(relative))}</loc>\n"
            f"    <lastmod>{REVIEW_DATE}</lastmod>\n"
            f"    <priority>{priority}</priority>\n"
            "  </url>"
        )
    return entries


def main() -> None:
    paths = sorted(ROOT.rglob("*.html"))
    totals = {"changed": 0, "exam_points": 0, "static_quiz": 0, "static_story": 0}
    for path in paths:
        result = improve_file(path)
        for key, value in result.items():
            totals[key] += int(value)
    sitemap = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "\n".join(sitemap_entries(paths))
        + "\n</urlset>\n"
    )
    (ROOT / "sitemap.xml").write_text(sitemap, encoding="utf-8")
    (ROOT / "robots.txt").write_text(
        "User-agent: *\nAllow: /\n\nSitemap: https://moduhistory.com/sitemap.xml\n", encoding="utf-8"
    )
    print(json.dumps({"html_files": len(paths), **totals}, ensure_ascii=False))


if __name__ == "__main__":
    main()
