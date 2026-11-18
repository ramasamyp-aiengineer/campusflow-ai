import httpx
import pytest
from fastapi.testclient import TestClient

from app.services.signals import (
    BRIEFING_XML,
    _cluster_for,
    analyze_sentiment,
    article_brief,
    fetch_feed,
    judge_item,
    local_brief,
    parse_feed,
    validate_public_url,
)


def test_semantic_filter_drops_unrelated_public_items():
    items = parse_feed(BRIEFING_XML)
    terms = {"sql", "fastapi", "python", "operating systems", "scheduling"}
    kept = [judge_item(item, terms) for item in items]
    titles = [item.raw.title for item in kept if item]
    assert any("SQL" in title for title in titles)
    assert all("derby" not in title.lower() and "canteen" not in title.lower() for title in titles)
    assert len(titles) < len(items)


def test_sentiment_reads_the_article_wording():
    label, _score, reason = analyze_sentiment("the api leaked a key and the service suffered an outage and breach")
    assert label == "Critical"
    assert "breach" in reason or "outage" in reason
    label, _score, reason = analyze_sentiment("hiring teams called the launch an opportunity for growth")
    assert label == "Positive"


def test_clusters_cover_more_than_one_topic():
    items = parse_feed(BRIEFING_XML)
    terms = {"sql", "fastapi", "python", "query", "index", "linux", "scheduler"}
    labels = {item.cluster_label for item in (judge_item(raw, terms) for raw in items) if item}
    assert "Databases" in labels or "Placement market" in labels
    assert len(labels) >= 2


def test_private_feeds_are_rejected():
    blocked = (
        "http://127.0.0.1/rss",
        "http://169.254.169.254/latest",
        "file:///tmp/feed.xml",
        "ftp://example.com/feed.xml",
        "http://localhost/rss",
        "http://10.0.0.8/rss",
        "http://172.16.4.2/rss",
        "http://192.168.1.10/rss",
        "http://[::1]/rss",
        "http://[::ffff:127.0.0.1]/rss",
        "http://user:pass@example.com/rss",
        "http://metadata.google.internal/computeMetadata/v1/",
    )
    for url in blocked:
        try:
            validate_public_url(url)
        except ValueError:
            continue
        raise AssertionError(url)


PUBLIC_FEED = "http://93.184.216.34/rss"


def test_redirect_to_a_private_address_is_refused():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(302, headers={"location": "http://169.254.169.254/latest/meta-data/"})

    with pytest.raises(ValueError, match="public"):
        fetch_feed(PUBLIC_FEED, transport=httpx.MockTransport(handler))


def test_oversized_feed_is_refused_while_streaming():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"<rss>" + b"x" * 600_000)

    with pytest.raises(ValueError, match="500KB"):
        fetch_feed(PUBLIC_FEED, transport=httpx.MockTransport(handler))


def test_feed_with_entity_declarations_is_refused():
    bomb = '<?xml version="1.0"?><!DOCTYPE lol [<!ENTITY lol "lol">]><rss><channel><item><title>&lol;</title><link>https://a.example/x</link></item></channel></rss>'
    with pytest.raises(ValueError, match="DOCTYPE"):
        parse_feed(bomb)


def test_feed_items_with_script_links_are_dropped():
    xml = (
        "<rss><channel>"
        "<item><title>Bad</title><link>javascript:alert(1)</link></item>"
        "<item><title>Good SQL story</title><link>https://a.example/sql</link></item>"
        "</channel></rss>"
    )
    assert [item.title for item in parse_feed(xml)] == ["Good SQL story"]


def test_words_inside_other_words_do_not_count():
    label, _score, _reason = analyze_sentiment("a bangalore startup opens a new office in the city")
    assert label == "Neutral"
    label, _score, _reason = analyze_sentiment("the company announced layoffs after the data breaches")
    assert label == "Critical"
    blob = "rapid growth in the capital market for authors"
    assert _cluster_for(blob)[0] != "Backend platforms"


def test_four_tone_labels_cover_every_case():
    assert analyze_sentiment("hiring growth and a scholarship launch")[0] == "Positive"
    assert analyze_sentiment("regulation brings risk and delay")[0] == "Watchful"
    assert analyze_sentiment("an outage and a breach hit the service")[0] == "Critical"
    assert analyze_sentiment("the committee met on tuesday")[0] == "Neutral"


def test_unnamed_stories_are_grouped_by_shared_keywords():
    from types import SimpleNamespace

    from app.services.signals import analyze_interest

    def story(story_id: int, title: str):
        return SimpleNamespace(
            id=story_id, title=title, summary="", source="Daily Paper", published_at="",
            sentiment="Neutral", sentiment_score=0, relevance_score=70, is_read=False,
        )

    stories = [
        story(1, "Bengaluru startup raises seed round for drones"),
        story(2, "Bengaluru metro opens a new line for commuters"),
        story(3, "Farmers adopt drones for crop spraying"),
        story(4, "Monsoon arrives early this season"),
    ]
    report = analyze_interest(stories, "Drones")
    labels = {cluster["label"] for cluster in report["clusters"]}
    assert "Bengaluru" in labels
    assert "General" not in labels
    assert sum(cluster["count"] for cluster in report["clusters"]) == 4
    assert report["clusters"][-1]["label"] == "Other stories"
    assert all(cluster["count"] >= 2 for cluster in report["clusters"] if cluster["label"] != "Other stories")
    assert all("drones" not in cluster["keywords"] for cluster in report["clusters"] if cluster["label"] != "Other stories")

    security = [story(5, "Phishing scam targets bank users"), story(6, "Hackers breach a hospital network"), story(7, "Bank phishing alerts rise")]
    labels = {cluster["label"] for cluster in analyze_interest(security, "Cybersecurity")["clusters"]}
    assert "Security" not in labels


def test_fallback_summary_is_two_sentences_at_most():
    text = local_brief("Title", "One sentence here. Two sentences here. Three is too many.", "SQL")
    assert text.startswith("For SQL:")
    assert "Three" not in text


def test_gemini_failure_falls_back_for_the_whole_batch(monkeypatch):
    from app.services import ai

    calls = []

    def failing(prompt: str, timeout: float = 25):
        calls.append(prompt)
        return None

    monkeypatch.setattr(ai, "_gemini_json", failing)
    brief, source = article_brief("A title about SQL joins", "A summary about SQL joins and indexes.", "SQL")
    assert source == "local"
    assert brief.startswith("For SQL:")
    assert len(calls) == 1


def test_failed_new_interest_is_not_saved(client: TestClient, monkeypatch):
    from app.services import signals

    def unreachable(url: str, transport=None) -> str:
        raise httpx.ConnectError("down")

    monkeypatch.setattr(signals, "fetch_feed", unreachable)
    before = len(client.get("/api/v1/signals", headers={"X-Persona": "student"}).json()["feeds"])
    failed = client.post(
        "/api/v1/signals/feeds",
        headers={"X-Persona": "student"},
        json={"url": PUBLIC_FEED, "label": "Unreachable"},
    )
    assert failed.status_code == 400
    after = len(client.get("/api/v1/signals", headers={"X-Persona": "student"}).json()["feeds"])
    assert after == before


def test_eight_hour_lock_and_inbox(client: TestClient):
    inbox = client.get("/api/v1/signals", headers={"X-Persona": "student"})
    assert inbox.status_code == 200
    body = inbox.json()
    assert body["messages"]
    assert body["clusters"]
    assert any("topic" in step.lower() for step in body["pipeline"])
    held = body["feeds"][0]["items_seen"] - body["feeds"][0]["items_kept"]
    assert held >= 1
    sentiments = {message["sentiment"] for message in body["messages"]}
    assert "Critical" in sentiments or "Watchful" in sentiments

    again = client.post(
        "/api/v1/signals/feeds",
        headers={"X-Persona": "student"},
        json={"url": body["feeds"][0]["url"], "label": "again"},
    )
    assert again.status_code == 409
    assert "8 hours" in again.json()["detail"]
    assert again.json()["detail"].startswith("Not yet")
    assert int(again.headers["Retry-After"]) > 0

    faculty = client.get("/api/v1/signals", headers={"X-Persona": "faculty"})
    assert faculty.status_code == 403
    pulse = client.get("/api/v1/signals/pulse", headers={"X-Persona": "faculty"})
    assert pulse.status_code == 200
    assert pulse.json()["message_count"] >= 1


def test_machine_learning_interest_drops_unrelated_items():
    from app.services.signals import ML_XML

    items = parse_feed(ML_XML)
    kept = [judge_item(item, {"sql"}, "Machine Learning") for item in items]
    titles = [item.raw.title for item in kept if item]
    assert any("neural" in title.lower() for title in titles)
    assert all("derby" not in title.lower() for title in titles)
    assert all(item.cluster_label == "Machine Learning" for item in kept if item)


def test_student_can_add_an_interest_topic(client: TestClient):
    created = client.post(
        "/api/v1/signals/feeds",
        headers={"X-Persona": "student"},
        json={"url": "builtin:machine-learning", "label": "Machine Learning"},
    )
    assert created.status_code == 200
    body = created.json()
    assert body["feed"]["label"] == "Machine Learning"
    assert body["kept"] >= 1
    assert body["held"] >= 1
    inbox = client.get("/api/v1/signals", headers={"X-Persona": "student"}).json()
    stories = [message for message in inbox["messages"] if message["subscription_id"] == body["feed"]["id"]]
    assert stories
    assert all(message["brief"] for message in stories)

    analysis = client.get(f"/api/v1/signals/feeds/{body['feed']['id']}/analysis", headers={"X-Persona": "student"})
    assert analysis.status_code == 200
    report = analysis.json()
    assert report["total"] == len(stories)
    assert sum(report["sentiments"].values()) == report["total"]
    assert len(report["rows"]) == report["total"]
    assert sum(cluster["count"] for cluster in report["clusters"]) == report["total"]
    assert all(cluster["keywords"] for cluster in report["clusters"])
    other = client.get(f"/api/v1/signals/feeds/{body['feed']['id']}/analysis", headers={"X-Persona": "faculty"})
    assert other.status_code == 403


def test_student_message_marks_read(client: TestClient):
    inbox = client.get("/api/v1/signals", headers={"X-Persona": "student"}).json()
    unread = next(message for message in inbox["messages"] if not message["is_read"])
    marked = client.patch(f"/api/v1/signals/messages/{unread['id']}/read", headers={"X-Persona": "student"})
    assert marked.status_code == 200
    assert marked.json()["is_read"] is True
