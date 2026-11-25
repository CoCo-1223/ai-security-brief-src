"""Hermes cron 브리핑 결과를 Fuwari 글로 바꿔 커밋·푸시한다.

~/.hermes/cron/output/<job_id>/*.md 중 성공한 실행의 "## Response" 부분을 날짜별 글
(src/content/posts/brief-YYYY-MM-DD.md)로 만든다. 같은 날 여러 번 실행됐으면 마지막 결과를 쓴다.
바뀐 게 없으면 아무것도 출력하지 않고 끝난다.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

JOB_ID = "df979d96af74"
OUTPUT_DIR = Path.home() / ".hermes" / "cron" / "output" / JOB_ID
REPO = Path(__file__).resolve().parent.parent
POSTS = REPO / "src" / "content" / "posts"
RUN_FILE = re.compile(r"^(\d{4}-\d{2}-\d{2})_\d{2}-\d{2}-\d{2}\.md$")
STATUS = re.compile(r"^\[(NEW|UPDATE|WATCH)\]", re.MULTILINE)


def extract_response(text: str) -> str | None:
    parts = re.split(r"^## Response\s*$", text, flags=re.MULTILINE)
    return parts[-1].strip() if len(parts) > 1 else None


def to_markdown(body: str) -> tuple[str, str]:
    lines = body.splitlines()
    # 제목·날짜 줄은 frontmatter의 title로 대체한다
    while lines and (not lines[0].strip() or "일일 브리핑" in lines[0] or re.fullmatch(r"\d{4}\.\d{2}\.\d{2}\s*", lines[0])):
        lines.pop(0)
    out = []
    for line in lines:
        s = line.rstrip()
        if m := re.fullmatch(r"━+\s*(.+?)\s*━+", s.strip()):
            s = f"## {m.group(1)}"
        elif s.strip() == "오늘의 핵심 변화 3줄":
            s = "## 오늘의 핵심 변화"
        elif s.strip().startswith("Sources:"):
            s = "## Sources"
        elif STATUS.match(s.strip()):
            s = f"### {s.strip()}"
        out.append(s.replace("?utm_source=openai", ""))
    md = "\n".join(out).strip() + "\n"
    first = next((l[2:].strip() for l in out if l.startswith("- ")), "AI·보안 일일 브리핑")
    return md, first


def build_post(date: str, body: str) -> str:
    md, desc = to_markdown(body)
    desc = desc.replace('"', "'")
    return (
        "---\n"
        f'title: "AI & Security 브리핑 {date.replace("-", ".")}"\n'
        f"published: {date}\n"
        f'description: "{desc}"\n'
        "tags: [AI, Security, Daily]\n"
        "category: Daily Brief\n"
        "lang: ko\n"
        "draft: false\n"
        "---\n\n"
        "> [!NOTE]\n"
        "> 이 글은 Hermes 에이전트가 자동으로 작성했습니다. 중요한 내용은 출처 원문을 확인하세요.\n\n"
        f"{md}"
    )


def git(*args: str) -> str:
    return subprocess.run(["git", "-C", str(REPO), *args], check=True, capture_output=True, text=True).stdout


def main() -> int:
    latest: dict[str, Path] = {}
    for f in sorted(OUTPUT_DIR.glob("*.md")):
        m = RUN_FILE.match(f.name)
        if m and extract_response(f.read_text(encoding="utf-8")):
            latest[m.group(1)] = f  # 정렬 순서상 마지막(가장 늦은 실행)이 남는다

    changed = []
    for date, f in latest.items():
        post = POSTS / f"brief-{date}.md"
        content = build_post(date, extract_response(f.read_text(encoding="utf-8")))
        if not post.exists() or post.read_text(encoding="utf-8") != content:
            post.write_text(content, encoding="utf-8")
            changed.append(post)

    if not changed:
        return 0
    try:
        git("add", *[str(p) for p in changed])
        git("commit", "-m", f"Daily brief: {', '.join(p.stem for p in changed)}")
        git("pull", "--rebase", "--quiet")
        git("push", "--quiet")
    except subprocess.CalledProcessError as e:
        print(f"publish_brief 실패: {' '.join(e.cmd[3:])}\n{e.stderr}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
