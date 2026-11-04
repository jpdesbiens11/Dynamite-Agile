"""Non-JSON HTTP responses: a handler returns a RawFile instead of a dict
to send a downloadable file (CSV export today; attachments/reports later).
"""


class RawFile:
    """A file response. `data` is bytes; the browser saves it as `filename`."""

    def __init__(self, data, filename, content_type="application/octet-stream", inline=False, export=None):
        self.data = data
        self.filename = filename
        self.content_type = content_type
        self.inline = inline  # shown in the page (images) rather than saved
        # Core lot v0.33 (D-B-129): a file built from the data (Word, Excel, PowerPoint, CSV, PDF) is stamped with its
        # revision and registered (core/stamp.py). export=False: a file people uploaded, sent back as it is.
        self.export = export

    @classmethod
    def image(cls, data, filename, mime):
        """An attachment displayed in a page. Content never changes for a
        given URL (content-addressed store), so the browser may cache it."""
        return cls(data, filename, mime, inline=True)

    @classmethod
    def csv(cls, text, filename):
        return cls(text.encode("utf-8-sig"), filename, "text/csv; charset=utf-8")
