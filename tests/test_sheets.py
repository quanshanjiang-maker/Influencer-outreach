from outreach.sheets import CANDIDATE_HEADERS, Sheet


class FakeWS:
    def __init__(self, header):
        self.header, self.col_count, self.writes = header, len(header), []

    def row_values(self, n):
        return list(self.header)

    def add_cols(self, n):
        self.col_count += n

    def update(self, range_name, values, value_input_option):
        self.header += values[0]

    def batch_update(self, data, value_input_option):
        self.writes += data


def test_old_sheet_gets_missing_columns_and_updates_by_name():
    ws = FakeWS(["date", "username", "status"])  # user reordered/trimmed columns
    sheet = Sheet.__new__(Sheet)
    sheet._cols, sheet.tabs = {}, {"candidates": "Candidates"}
    sheet.book = type("B", (), {"worksheet": lambda self, t: ws})()
    sheet.update_candidates([(5, {"status": "sent", "sent_at": "now"})])
    assert ws.header[:3] == ["date", "username", "status"] and set(CANDIDATE_HEADERS) <= set(ws.header)
    ranges = {d["range"] for d in ws.writes}
    assert "C5" in ranges and f"{chr(64 + ws.header.index('sent_at') + 1)}5" in ranges
