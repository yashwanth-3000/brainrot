from brainrot_backend.video_generator.integrations.firecrawl import extract_candidate_urls, rank_site_urls


def test_rank_site_urls_prioritizes_content_paths():
    ranked = rank_site_urls(
        "https://example.com",
        [
            "https://example.com/",
            "https://example.com/privacy",
            "https://example.com/blog/how-to-build",
            "https://example.com/docs/setup",
            "https://example.com/tag/python",
        ],
    )
    assert ranked[:2] == [
        "https://example.com/blog/how-to-build",
        "https://example.com/docs/setup",
    ]
    assert "https://example.com/privacy" not in ranked


def test_extract_candidate_urls_supports_firecrawl_map_objects():
    urls = extract_candidate_urls(
        [
            {"url": "https://example.com/blog/post-one", "title": "Post One"},
            {"sourceURL": "https://example.com/docs/setup"},
            "https://example.com/research/report",
        ]
    )
    assert urls == [
        "https://example.com/blog/post-one",
        "https://example.com/docs/setup",
        "https://example.com/research/report",
    ]
