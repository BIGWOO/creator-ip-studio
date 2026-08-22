from creator_ip_studio.pipeline import _captions, _timestamp


def test_timestamp_is_srt_compatible():
    assert _timestamp(61.234) == "00:01:01,234"


def test_captions_cover_requested_duration():
    captions = _captions("First sentence. Second sentence.", 20)
    assert "00:00:00,000 --> 00:00:09,950" in captions
    assert "00:00:10,000 --> 00:00:19,950" in captions

