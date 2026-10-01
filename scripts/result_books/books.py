"""The four held SEC result books and the page interval holding each one's results."""

import dataclasses
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]


@dataclasses.dataclass(frozen=True)
class Book:
    key: str
    source_relative: str
    source_sha256: str
    first_page: int
    last_page: int
    # Only the 2010 Zila Parishad parser uses font name and size to read its layout.
    font_attributes: bool = False

    @property
    def source(self):
        return ROOT / self.source_relative

    @property
    def extracted(self):
        return ROOT / f"data/extracted/{self.key}_pages.jsonl"

    @property
    def parsed(self):
        return ROOT / f"data/fin/{self.key}_std.parquet"


BOOKS = {
    book.key: book
    for book in (
        Book(
            "panchayat_samiti_2005",
            "data/source/panchayat_samiti/panchayat_samiti_2005.pdf",
            "ef08fe1925432f9f644c9a53ce13803521d095448c98855a1feb0425e7af881e",
            111,
            180,
        ),
        Book(
            "panchayat_samiti_2010",
            "data/source/panchayat_samiti/panchayat_samiti_2010.pdf",
            "e88f62d7e7172612310c66e73d90b475c2fb48494c57906fea6153dbce8c14c7",
            206,
            349,
        ),
        Book(
            "zila_parishad_2005",
            "data/source/zilla_parishad/zila_parishad_2005.pdf",
            "66c69e85b27b2ef39f7548c4d95d1640d76ec44349300a6837f8670b499f74dc",
            54,
            82,
        ),
        Book(
            "zila_parishad_2010",
            "data/source/zilla_parishad/zila_parishad_2010.pdf",
            "4399f7b9943ff6f71b3c728c21a2161696675fcbf17d47138af1938ca10a0272",
            74,
            98,
            font_attributes=True,
        ),
    )
}
