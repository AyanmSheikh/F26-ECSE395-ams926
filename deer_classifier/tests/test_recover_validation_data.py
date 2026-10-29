"""Range safety and split/sampling checks without network or real dataset downloads."""

import io
import re
import sys
import unittest
from pathlib import Path
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from recover_validation_data import HTTPRangeFile, negative_samples, positive_members


class Response(io.BytesIO):
    def __init__(self, payload, status, headers):
        super().__init__(payload)
        self.status, self.headers = status, headers
        self.read_calls = 0

    def read(self, size=-1):
        self.read_calls += 1
        return super().read(size)


class RecoveryTests(unittest.TestCase):
    def test_remote_zip_seeks_ranges_and_reuses_small_blocks(self):
        stream = io.BytesIO()
        with zipfile.ZipFile(stream, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("deer.txt", b"deer reference" * 20000)
        payload = stream.getvalue()
        requests = []

        def opener(request, timeout):
            start, end = map(int, re.fullmatch(r"bytes=(\d+)-(\d+)", request.get_header("Range")).groups())
            requests.append((start, end))
            return Response(payload[start:end + 1], 206, {"Content-Range": f"bytes {start}-{end}/{len(payload)}"})

        remote = HTTPRangeFile("https://example.invalid/archive", opener=opener, block_size=64)
        with zipfile.ZipFile(remote) as archive:
            self.assertEqual(archive.read("deer.txt"), b"deer reference" * 20000)
        remote.seek(0)
        remote.read(4)
        count = len(requests)
        remote.seek(1)
        self.assertEqual(remote.read(3), payload[1:4])
        self.assertEqual(len(requests), count)

    def test_server_ignoring_range_is_rejected_before_reading_body(self):
        response = Response(b"huge archive must not be read", 200, {})
        with self.assertRaisesRegex(ValueError, "did not honor"):
            HTTPRangeFile("https://example.invalid/archive", opener=lambda *args, **kwargs: response)
        self.assertEqual(response.read_calls, 0)

    def test_positive_selection_excludes_training_cameras_and_source_test(self):
        stream = io.BytesIO()
        with zipfile.ZipFile(stream, "w") as archive:
            for split, location in (("train", "loc_0012"), ("valid", "loc_0003"), ("test", "loc_0012")):
                stem = f"{location}_im_000001"
                archive.writestr(f"Lila.v1.3k/{split}/images/{stem}.jpg", b"image")
                archive.writestr(f"Lila.v1.3k/{split}/labels/{stem}.txt", b"0 .5 .5 .5 .5")
        stream.seek(0)
        with zipfile.ZipFile(stream) as archive:
            pairs = positive_members(archive)
        self.assertEqual(len(pairs), 1)
        self.assertIn("train/images/loc_0012", pairs[0][0])

    def test_negative_sampling_keeps_sequences_excludes_deer_and_round_robins(self):
        images = [
            {"id": "b1", "seq_id": "bird1", "file_name": "loc_0012/bird1.jpg"},
            {"id": "b2", "seq_id": "bird1", "file_name": "loc_0012/bird2.jpg"},
            {"id": "e1", "seq_id": "empty1", "file_name": "loc_0012/empty1.jpg"},
            {"id": "d1", "seq_id": "mixed_deer", "file_name": "loc_0012/deer.jpg"},
        ]
        metadata = {"images": images, "categories": [{"id": 1, "name": "bird"}, {"id": 2, "name": "empty"}, {"id": 3, "name": "deer"}],
                    "annotations": [{"image_id": "b1", "category_id": 1}, {"image_id": "e1", "category_id": 2},
                                    {"image_id": "d1", "category_id": 1}, {"image_id": "d1", "category_id": 3}]}
        result = negative_samples(metadata, 2)
        self.assertEqual([row["source_path"] for row in result], ["loc_0012/bird1.jpg", "loc_0012/empty1.jpg"])
        with self.assertRaisesRegex(ValueError, "only 2"):
            negative_samples(metadata, 3)


if __name__ == "__main__":
    unittest.main()
