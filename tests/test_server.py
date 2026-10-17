"""Offline tests for the ScreenApp MCP server.

Response fixtures mirror the real ``https://screenapp.io/app/api/v1`` shapes
captured from the live API:

  GET /videos                  -> {"videos": [...]}
  GET /videos/{id}             -> flat video record incl. transcriptStatus/transcriptMeta
  GET /videos/{id}/transcript  -> flat object with top-level text/segments/words
                                  (there is NO wrapper ``transcript`` key)

Run with:  python -m unittest discover -s tests -v
"""
import asyncio
import sys
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import server  # noqa: E402


def run(coro):
    return asyncio.run(coro)


VIDEO_LIST = {
    "videos": [
        {
            "id": "aaaaaaaaaaaaaaaaaaaaaaaa",
            "name": "Lecture 1",
            "duration": 125.5,
            "status": "ready",
            "transcriptStatus": "ready",
            "mimeType": "video/mp4",
            "size": 1024,
            "createdAt": "2026-09-01T10:00:00.000Z",
        }
    ]
}

VIDEO_DETAIL = {
    "id": "aaaaaaaaaaaaaaaaaaaaaaaa",
    "name": "Lecture 1",
    "duration": 125.5,
    "status": "ready",
    "transcriptStatus": "ready",
    "mimeType": "video/mp4",
    "size": 1024,
    "createdAt": "2026-09-01T10:00:00.000Z",
    "updatedAt": "2026-09-01T10:05:00.000Z",
    "error": None,
    "transcriptMeta": {
        "_id": "t1",
        "language": "English",
        "duration": 125.5,
        "segmentCount": 2,
        "provider": "xai",
        "detectedLanguages": ["en"],
    },
}

# Captured verbatim from GET /videos/{id}/transcript: text and segments are
# top-level keys, not nested under a "transcript" property.
TRANSCRIPT_FLAT = {
    "text": "hello world second line",
    "segments": [
        {"id": 0, "start": 0.0, "end": 1.5, "speaker": "Speaker 1",
         "text": "hello world", "words": []},
        {"id": 1, "start": 1.5, "end": 3.0, "speaker": "Speaker 2",
         "text": "second line", "words": []},
    ],
    "compact_segments": [
        {"id": 0, "start": 0.0, "end": 1.5, "speaker": "Speaker 1",
         "text": "hello world", "no_speech": False},
    ],
    "words": [],
    "language": "en",
    "duration": 125.5,
    "meta": {"provider": "xai", "total_segments": 2},
    "task": "transcribe",
    "video_extracted_info": {"videoType": "screencast", "speakers": []},
    "file_version": "1",
    "program_version": "1",
}


class TransportTests(unittest.TestCase):
    def test_uses_v1_base_url_and_api_key_header(self):
        self.assertEqual(server.BASE_URL, "https://screenapp.io/app/api/v1")
        self.assertIn("x-api-key", server.client.headers)

    def test_health_reports_v1(self):
        body = run(server.health())
        self.assertEqual(body["status"], "healthy")
        self.assertEqual(body["api"], "v1")
        self.assertEqual(body["tools"], len(server.TOOLS))


class McpProtocolTests(unittest.TestCase):
    def test_initialize_reports_server_info(self):
        reply = run(server.handle_request({"id": 1, "method": "initialize"}))
        self.assertEqual(reply["result"]["serverInfo"]["name"], "screenapp-mcp")

    def test_tools_list_matches_implementations(self):
        reply = run(server.handle_request({"id": 2, "method": "tools/list"}))
        listed = {tool["name"] for tool in reply["result"]["tools"]}
        self.assertEqual(listed, set(server.TOOL_IMPLEMENTS))

    def test_unknown_tool_is_reported_as_error(self):
        out = run(server.execute_tool("nope", {}))
        self.assertTrue(out.startswith("❌"))

    def test_tools_call_flags_errors(self):
        reply = run(server.handle_request({
            "id": 3,
            "method": "tools/call",
            "params": {"name": "get_video_info", "arguments": {}},
        }))
        self.assertTrue(reply["result"]["isError"])


class ToolTests(unittest.TestCase):
    def test_list_videos_formats_rows(self):
        with patch.object(server, "_get", AsyncMock(return_value=(200, VIDEO_LIST))):
            out = run(server.execute_tool("list_videos", {"limit": 5}))
        self.assertIn("Lecture 1", out)
        self.assertIn("transcriptStatus=ready", out)

    def test_list_videos_clamps_limit(self):
        getter = AsyncMock(return_value=(200, VIDEO_LIST))
        with patch.object(server, "_get", getter):
            run(server.execute_tool("list_videos", {"limit": 5000}))
        self.assertEqual(getter.await_args.kwargs["params"]["limit"], 100)

    def test_get_video_info_requires_id(self):
        out = run(server.execute_tool("get_video_info", {}))
        self.assertIn("videoId", out)

    def test_get_video_info_reports_transcript_state(self):
        with patch.object(server, "_get", AsyncMock(return_value=(200, VIDEO_DETAIL))):
            out = run(server.execute_tool("get_video_info", {"videoId": "x"}))
        self.assertIn("transcriptStatus: ready", out)

    def test_transcript_parses_flat_v1_payload(self):
        """Live API returns text/segments at top level, not under 'transcript'."""
        with patch.object(server, "_get",
                          AsyncMock(side_effect=[(200, VIDEO_DETAIL), (200, TRANSCRIPT_FLAT)])):
            out = run(server.execute_tool(
                "get_video_transcript", {"videoId": "x", "max_chars": 8000}))
        self.assertIn("hello world second line", out)
        self.assertNotIn("Unexpected transcript response", out)

    def test_transcript_falls_back_to_segments(self):
        no_text = dict(TRANSCRIPT_FLAT)
        no_text.pop("text")
        with patch.object(server, "_get",
                          AsyncMock(side_effect=[(200, VIDEO_DETAIL), (200, no_text)])):
            out = run(server.execute_tool("get_video_transcript", {"videoId": "x"}))
        self.assertIn("[0s] Speaker 1: hello world", out)
        self.assertIn("[2s] Speaker 2: second line", out)

    def test_transcript_truncates_with_accurate_count(self):
        with patch.object(server, "_get",
                          AsyncMock(side_effect=[(200, VIDEO_DETAIL), (200, TRANSCRIPT_FLAT)])):
            out = run(server.execute_tool(
                "get_video_transcript", {"videoId": "x", "max_chars": 10}))
        self.assertIn(f"Truncated to 10 chars of {len(TRANSCRIPT_FLAT['text'])}", out)

    def test_transcript_handles_409(self):
        with patch.object(server, "_get",
                          AsyncMock(side_effect=[(200, VIDEO_DETAIL), (409, {"error": "not ready"})])):
            out = run(server.execute_tool("get_video_transcript", {"videoId": "x"}))
        self.assertIn("409", out)

    def test_transcript_handles_api_error(self):
        with patch.object(server, "_get",
                          AsyncMock(side_effect=[(401, {"error": "Unauthorized"}), (0, {})])):
            out = run(server.execute_tool("get_video_transcript", {"videoId": "x"}))
        self.assertIn("401", out)

    def test_transcript_rejects_unexpected_payload(self):
        with patch.object(server, "_get",
                          AsyncMock(side_effect=[(200, VIDEO_DETAIL), (200, {"unexpected": True})])):
            out = run(server.execute_tool("get_video_transcript", {"videoId": "x"}))
        self.assertIn("Unexpected transcript response", out)

    def test_upload_requires_url(self):
        out = run(server.execute_tool("upload_video", {}))
        self.assertIn("url", out)

    def test_upload_reports_new_id(self):
        with patch.object(server, "_post",
                          AsyncMock(return_value=(202, {"data": {"id": "newid"}}))):
            out = run(server.execute_tool("upload_video", {"url": "https://x/y.mp4"}))
        self.assertIn("newid", out)


if __name__ == "__main__":
    unittest.main(verbosity=2)