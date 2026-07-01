"""
Telegram OSINT 수집 — 공개 채널 프리뷰(t.me/s/<channel>) 스크래핑.
인증 불필요. 분쟁/전쟁 관련 공개 채널의 최신 메시지를 이벤트 dict로 변환한다.

RSS 수집기와 동일한 패턴: 텍스트 기반 → casualty_extractor 가 사망자 추정,
event_linker 가 국가를 추출하는 하류 단계로 넘긴다.
"""
import re
import html
import requests
from datetime import datetime, timedelta


def _clean(raw: str) -> str:
    """메시지 HTML → 평문."""
    t = re.sub(r"<br\s*/?>", " ", raw)
    t = re.sub(r"</?(?:b|i|s|u|a|span|tg-emoji|code|pre)[^>]*>", "", t)
    t = re.sub(r"<[^>]+>", "", t)
    t = html.unescape(t)
    return re.sub(r"\s+", " ", t).strip()


def _parse_preview(channel: str, page: str, cutoff: datetime) -> list[dict]:
    """t.me/s/<channel> HTML 에서 메시지들을 파싱."""
    results = []
    # 각 메시지는 js-widget_message 컨테이너로 시작 (data-post 보유)
    blocks = re.split(r'js-widget_message\b', page)
    for blk in blocks:
        m_post = re.search(r'data-post="([^"]+)"', blk)
        m_text = re.search(
            r'tgme_widget_message_text[^"]*"[^>]*>(.*?)</div>', blk, re.DOTALL
        )
        if not (m_post and m_text):
            continue
        text = _clean(m_text.group(1))
        if len(text) < 25:
            continue

        # 날짜 (message footer 의 <time datetime="...">)
        dt = None
        m_time = re.search(r'<time[^>]+datetime="([^"]+)"', blk)
        if m_time:
            try:
                dt = datetime.fromisoformat(
                    m_time.group(1).replace("Z", "+00:00")
                ).replace(tzinfo=None)
            except ValueError:
                dt = None
        if dt and dt < cutoff:
            continue

        post = m_post.group(1)  # "channel/12345"
        results.append({
            "source": f"telegram/{channel}",
            "title": text[:140],
            "summary": text[:500],
            "url": f"https://t.me/{post}",
            "date": dt.strftime("%Y-%m-%d") if dt else "",
            "feed_name": f"TG:{channel}",
            "channel": channel,
        })
    return results


def fetch_telegram(channels: list[str], per_channel: int = 12, days: int = 3) -> list[dict]:
    """공개 Telegram 채널들에서 최근 메시지 수집."""
    cutoff = datetime.now() - timedelta(days=days)
    out = []
    for ch in channels:
        try:
            r = requests.get(
                f"https://t.me/s/{ch}",
                timeout=15,
                headers={"User-Agent": "Mozilla/5.0 (compatible; conflict-monitor/1.0)"},
            )
            if r.status_code != 200:
                print(f"    [telegram:{ch}] HTTP {r.status_code}")
                continue
            msgs = _parse_preview(ch, r.text, cutoff)
            out.extend(msgs[-per_channel:])
        except Exception as e:
            print(f"    [telegram:{ch}] 실패: {e}")
            continue
    return out


if __name__ == "__main__":
    chans = ["intelslava", "worldsource24", "war_monitor", "Faytuks", "spectatorindex"]
    evs = fetch_telegram(chans, per_channel=5, days=7)
    print(f"collected {len(evs)} telegram messages")
    for e in evs[:8]:
        print(f"  [{e['channel']}] {e['date']} | {e['title'][:80]}")
