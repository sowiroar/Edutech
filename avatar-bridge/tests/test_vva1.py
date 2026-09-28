import json
import uuid

import pytest

import vva1

SESSION = uuid.UUID("00112233-4455-6677-8899-aabbccddeeff")
UTTERANCE = uuid.UUID("ffeeddcc-bbaa-9988-7766-554433221100")


def unreal_guid(raw: bytes) -> str:
    """ReadGuid + FGuid::ToString(DigitsWithHyphens) del receptor C++."""
    a, b, c, d = (int.from_bytes(raw[i : i + 4], "big") for i in (0, 4, 8, 12))
    return (
        f"{a:08X}-{b >> 16:04X}-{b & 0xFFFF:04X}-{c >> 16:04X}-{c & 0xFFFF:04X}{d:08X}"
    )


def test_header_layout_matches_receiver():
    pcm = b"\x01\x00\x02\x00\x03\x00"
    packet = vva1.encode_audio_packet(SESSION, UTTERANCE, 0x0000000100000002, pcm)
    assert packet[:4] == b"VVA1"
    assert unreal_guid(packet[4:20]) == str(SESSION).upper()
    assert unreal_guid(packet[20:36]) == str(UTTERANCE).upper()
    offset = (int.from_bytes(packet[36:40], "big") << 32) | int.from_bytes(
        packet[40:44], "big"
    )
    assert offset == 0x0000000100000002
    assert packet[44:] == pcm
    assert len(packet) == 44 + len(pcm)


def test_roundtrip():
    packet = vva1.encode_audio_packet(SESSION, UTTERANCE, 960, b"\x10\x00" * 5)
    decoded = vva1.decode_audio_packet(packet)
    assert (decoded.session, decoded.utterance, decoded.offset) == (
        SESSION,
        UTTERANCE,
        960,
    )
    assert decoded.pcm == b"\x10\x00" * 5


@pytest.mark.parametrize("pcm", [b"", b"\x01"])
def test_encode_rejects_incomplete_samples(pcm):
    with pytest.raises(ValueError):
        vva1.encode_audio_packet(SESSION, UTTERANCE, 0, pcm)


def test_encode_rejects_oversized_packet():
    too_big = b"\x00\x00" * (vva1.MAX_PACKET_BYTES // 2)
    with pytest.raises(ValueError):
        vva1.encode_audio_packet(SESSION, UTTERANCE, 0, too_big)


@pytest.mark.parametrize(
    "packet",
    [b"VVA1" + b"\x00" * 40, b"XXXX" + b"\x00" * 42, b"VVA1" + b"\x00" * 41],
)
def test_decode_rejects_bad_frames(packet):
    with pytest.raises(ValueError):
        vva1.decode_audio_packet(packet)


def test_control_envelopes():
    for text, kind in [
        (vva1.ready(SESSION), "ready"),
        (vva1.state_changed(SESSION, "listening"), "state_changed"),
        (vva1.audio_start(SESSION, UTTERANCE), "audio_start"),
        (vva1.audio_end(SESSION, UTTERANCE, 4800), "audio_end"),
        (vva1.cancel(SESSION, UTTERANCE), "cancel"),
    ]:
        message = json.loads(text)
        assert message["type"] == kind
        assert message["version"] == 1
        assert message["session_id"] == str(SESSION)
    start = json.loads(vva1.audio_start(SESSION, UTTERANCE))
    assert (start["sample_rate"], start["channels"], start["encoding"]) == (
        48000,
        1,
        "pcm_s16le",
    )
    assert json.loads(vva1.audio_end(SESSION, UTTERANCE, 4800))["total_samples"] == 4800


def test_state_changed_rejects_unknown_state():
    with pytest.raises(ValueError):
        vva1.state_changed(SESSION, "dancing")
