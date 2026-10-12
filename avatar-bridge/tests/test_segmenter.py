from array import array

from segmenter import End, Pcm, Segmenter, Start, peak


def frame(amplitude: int, samples: int = 960) -> bytes:
    return array("h", [amplitude] * samples).tobytes()


def kinds(events):
    return [e.kind for e in events]


def test_peak():
    assert peak(frame(1234)) == 1234
    assert peak(array("h", [-32768, 5]).tobytes()) == 32768
    assert peak(b"") == 0


def test_silence_before_speech_is_ignored():
    seg = Segmenter(silence_seconds=0.5)
    assert seg.feed(frame(0), 0.0) == []
    assert not seg.is_open


def test_speech_opens_streams_and_silence_closes():
    seg = Segmenter(silence_seconds=0.5)
    events = seg.feed(frame(5000), 0.00)
    assert kinds(events) == ["start", "pcm"]
    assert kinds(seg.feed(frame(5000), 0.02)) == ["pcm"]
    assert kinds(seg.feed(frame(0), 0.30)) == ["pcm"]  # silencio corto: sigue abierto
    assert kinds(seg.feed(frame(0), 0.60)) == ["pcm", "end"]
    assert not seg.is_open


def test_tick_closes_when_frames_stop_arriving():
    seg = Segmenter(silence_seconds=0.5)
    seg.feed(frame(5000), 1.0)
    assert seg.tick(1.2) == []
    assert kinds(seg.tick(1.6)) == ["end"]
    assert seg.tick(9.0) == []


def test_voice_resets_the_silence_window():
    seg = Segmenter(silence_seconds=0.5)
    seg.feed(frame(5000), 0.0)
    seg.feed(frame(0), 0.4)
    assert kinds(seg.feed(frame(5000), 0.8)) == ["pcm"]  # la voz vuelve antes del corte
    assert seg.is_open


def test_new_utterance_after_end():
    seg = Segmenter(silence_seconds=0.5)
    seg.feed(frame(5000), 0.0)
    seg.tick(1.0)
    assert kinds(seg.feed(frame(5000), 2.0)) == ["start", "pcm"]


def test_reset_drops_open_utterance():
    seg = Segmenter()
    seg.feed(frame(5000), 0.0)
    seg.reset()
    assert not seg.is_open and seg.tick(99.0) == []


def test_pcm_event_keeps_bytes():
    seg = Segmenter()
    data = frame(4000)
    events = seg.feed(data, 0.0)
    assert events == [Start(), Pcm(data)]
    assert End().kind == "end"
