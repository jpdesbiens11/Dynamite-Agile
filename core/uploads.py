"""Shared attachment store (core lot v0.4, D-B-003; closes Q-04).

One place where every module keeps the files users add: images pasted in
a Dynamite page today, ticket attachments later. A module never writes
to disk itself; it calls store() and serves the file back with
RawFile.image() after checking the reader's role on the project.

- Upload transport: a route handler decorated with @binary_body receives
  the raw request body (not JSON) in ctx.upload -- see core/router.py.
  Size is capped by "max_upload_mb" in data/config.json.
- Type: decided from the file's first bytes (magic numbers), never from
  the name or the Content-Type sent by the browser. SVG is refused: it
  can carry script.
- Storage: data/attachments/<project_id>/<sha256[:2]>/<sha256>.<ext>,
  content-addressed, so the same image pasted twice is stored once.
  Files are never deleted by a page edit (restoring an old version must
  still show its images); a cleanup of orphans is a later decision.
"""
import hashlib
import io
import zipfile
from pathlib import Path

from . import db
from .errors import ApiError

MIGRATIONS = [
    (1, """
        CREATE TABLE attachments (
            id            INTEGER PRIMARY KEY,
            project_id    INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
            module        TEXT NOT NULL,
            sha256        TEXT NOT NULL,
            mime          TEXT NOT NULL,
            size          INTEGER NOT NULL,
            original_name TEXT NOT NULL DEFAULT '',
            created_by    INTEGER REFERENCES users(id) ON DELETE SET NULL,
            created_at    TEXT NOT NULL,
            UNIQUE (project_id, module, sha256)
        );
    """),
]

IMAGE_TYPES = {  # mime -> (extension, magic-number test)
    "image/png": ("png", lambda b: b.startswith(b"\x89PNG\r\n\x1a\n")),
    "image/jpeg": ("jpg", lambda b: b.startswith(b"\xff\xd8\xff")),
    "image/gif": ("gif", lambda b: b[:6] in (b"GIF87a", b"GIF89a")),
    "image/webp": ("webp", lambda b: b[:4] == b"RIFF" and b[8:12] == b"WEBP"),
}
IMAGE_LABEL = "PNG, JPEG, GIF ou WebP"
DOC_TYPES = {"application/pdf": ("pdf", lambda b: b.startswith(b"%PDF-")),  # core lot v0.20 (D-A-048): results reports
             # core lot v0.32 (D-B-114): 3D models (ISO 10303-21, « STEP »), read in the browser (3D viewers)
             "model/step": ("stp", lambda b: b.lstrip(b"\xef\xbb\xbf \t\r\n")[:13] == b"ISO-10303-21;")}


# core lot v0.35: evidence files of a test campaign -- Office documents, text logs, archives. Never served inline.
OFFICE_TYPES = {  # mime -> (extension, folder that every file of that format has in its zip)
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ("docx", "word/"),
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ("xlsx", "xl/"),
    "application/vnd.openxmlformats-officedocument.presentationml.presentation": ("pptx", "ppt/"),
}
EVIDENCE_TYPES = dict({m: (e, None) for m, (e, _) in OFFICE_TYPES.items()},
                      **{"application/zip": ("zip", None), "text/plain": ("txt", None)})
EVIDENCE_LABEL = "PDF, Word, Excel, PowerPoint, images (PNG, JPEG, GIF, WebP), texte (.txt, .csv, .log) ou zip"


class Upload:
    """Raw request body handed to a @binary_body handler."""

    def __init__(self, data, content_type, filename):
        self.data = data
        self.content_type = content_type
        self.filename = filename


def binary_body(handler):
    """Mark a route handler as taking a raw file body instead of JSON."""
    handler.accepts_binary = True
    return handler


def sniff_image(data):
    for mime, (_, test) in IMAGE_TYPES.items():
        if test(data):
            return mime
    return None


def _clean_name(name):
    name = (name or "").replace("\\", "/").rsplit("/", 1)[-1]
    return "".join(ch for ch in name if ch.isprintable() and ch not in '"<>')[:120]


def _root(data_dir):
    return Path(data_dir) / "attachments"


def store_image(ctx, project_id, module, max_bytes):
    """Validate ctx.upload as an image and store it. Returns the row dict."""
    upload = getattr(ctx, "upload", None)
    if upload is None or not upload.data:
        raise ApiError(400, "Aucun fichier reçu. Correctif : collez, glissez ou choisissez une image.")
    if len(upload.data) > max_bytes:
        raise ApiError(413, "Image de {:.1f} Mo. Correctif : {} Mo au maximum ; réduisez-la ou "
                            "exportez-la en JPEG.".format(len(upload.data) / 1048576, max_bytes // 1048576))
    mime = sniff_image(upload.data)
    if mime is None:
        raise ApiError(415, "Ce fichier n'est pas une image reconnue. Correctif : formats acceptés "
                            ": {} (le SVG est refusé, il peut contenir du script).".format(IMAGE_LABEL))
    return _store(ctx, project_id, module, upload, mime)


def store_pdf(ctx, project_id, module, max_bytes):
    """Validate ctx.upload as a PDF (by its first bytes) and store it (core lot v0.20). Returns the row dict."""
    upload = getattr(ctx, "upload", None)
    if upload is None or not upload.data:
        raise ApiError(400, "Aucun fichier reçu. Correctif : choisissez le rapport PDF.")
    if len(upload.data) > max_bytes:
        raise ApiError(413, "PDF de {:.1f} Mo. Correctif : {} Mo au maximum (compressez-le ou demandez à l'administrateur "
                            "d'augmenter « max_upload_mb »).".format(len(upload.data) / 1048576, max_bytes // 1048576))
    if not DOC_TYPES["application/pdf"][1](upload.data):
        raise ApiError(415, "Ce fichier n'est pas un PDF (« {} »). Correctif : exportez ou imprimez le rapport en PDF, "
                            "puis joignez ce fichier.".format(_clean_name(upload.filename) or "sans nom"))
    return _store(ctx, project_id, module, upload, "application/pdf")


def store_step(ctx, project_id, module, max_bytes):
    """Validate ctx.upload as a STEP model (ISO 10303-21 header) and store it (core lot v0.32). Returns the row dict."""
    upload = getattr(ctx, "upload", None)
    if upload is None or not upload.data:
        raise ApiError(400, "Aucun fichier reçu. Correctif : choisissez le fichier STEP (.stp ou .step).")
    if len(upload.data) > max_bytes:
        raise ApiError(413, "STEP de {:.1f} Mo. Correctif : {} Mo au maximum ; exportez seulement la zone à analyser, ou "
                            "demandez à l'administrateur d'augmenter « max_upload_mb ».".format(
                                len(upload.data) / 1048576, max_bytes // 1048576))
    if not DOC_TYPES["model/step"][1](upload.data[:64]):
        raise ApiError(415, "Ce fichier n'est pas un STEP (« {} » ne commence pas par ISO-10303-21). Correctif : dans le "
                            "logiciel de CAO, exportez l'assemblage en STEP AP214 ou AP242.".format(
                                _clean_name(upload.filename) or "sans nom"))
    return _store(ctx, project_id, module, upload, "model/step")


def sniff_evidence(data):
    """The mime of an evidence file from its bytes, or (None, reason). Macros and active content are refused."""
    mime = sniff_image(data)
    if mime:
        return mime, ""
    if DOC_TYPES["application/pdf"][1](data):
        return "application/pdf", ""
    if data[:4] == b"PK\x03\x04":
        try:
            names = zipfile.ZipFile(io.BytesIO(data)).namelist()
        except (zipfile.BadZipFile, OSError, ValueError):
            return None, "archive zip illisible"
        if any(n.lower().endswith(("vbaproject.bin", ".exe", ".dll", ".js", ".vbs", ".bat", ".cmd", ".scr")) for n in names):
            return None, "elle contient des macros ou du code exécutable"
        for mime, (_, folder) in OFFICE_TYPES.items():
            if "[Content_Types].xml" in names and any(n.startswith(folder) for n in names):
                return mime, ""
        return "application/zip", ""
    head = data[:4096]
    if b"\x00" not in head:
        try:
            head.decode("utf-8", "strict")
        except UnicodeDecodeError as err:
            if err.start < len(head) - 4:  # a cut multi-byte character at the end of the sample is fine
                return None, "type de fichier non reconnu"
        return "text/plain", ""
    return None, "type de fichier non reconnu"


def store_evidence(ctx, project_id, module, max_bytes):
    """Validate ctx.upload as an evidence file (core lot v0.35) and store it. Returns the row dict."""
    upload = getattr(ctx, "upload", None)
    if upload is None or not upload.data:
        raise ApiError(400, "Aucun fichier reçu. Correctif : choisissez le fichier de preuve.")
    if len(upload.data) > max_bytes:
        raise ApiError(413, "Fichier de {:.1f} Mo. Correctif : {} Mo au maximum (compressez-le, ou demandez à l'administrateur "
                            "d'augmenter « max_upload_mb »).".format(len(upload.data) / 1048576, max_bytes // 1048576))
    mime, why = sniff_evidence(upload.data)
    if mime is None:
        raise ApiError(415, "« {} » refusé : {}. Correctif : formats acceptés : {} ; enregistrez le document sans macros "
                            "(.docx, .xlsx, .pptx).".format(_clean_name(upload.filename) or "sans nom", why, EVIDENCE_LABEL))
    return _store(ctx, project_id, module, upload, mime)


def _store(ctx, project_id, module, upload, mime):
    conn = ctx.conn
    digest = hashlib.sha256(upload.data).hexdigest()
    existing = conn.execute("SELECT * FROM attachments WHERE project_id = ? AND module = ? AND sha256 = ?",
                            (project_id, module, digest)).fetchone()
    path = file_path(ctx.data_dir, project_id, digest, mime)
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + ".part")
        tmp.write_bytes(upload.data)
        tmp.replace(path)  # atomic: a reader never sees half a file
    if existing is not None:
        return dict(existing)
    new_id = conn.execute(
        "INSERT INTO attachments (project_id, module, sha256, mime, size, original_name, created_by, "
        "created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (project_id, module, digest, mime, len(upload.data), _clean_name(upload.filename),
         ctx.user["id"], db.utc_now())).lastrowid
    return dict(conn.execute("SELECT * FROM attachments WHERE id = ?", (new_id,)).fetchone())


def file_path(data_dir, project_id, digest, mime):
    ext = (IMAGE_TYPES.get(mime) or DOC_TYPES.get(mime) or EVIDENCE_TYPES.get(mime) or ("bin", None))[0]
    return _root(data_dir) / str(int(project_id)) / digest[:2] / "{}.{}".format(digest, ext)


def read(data_dir, row):
    path = file_path(data_dir, row["project_id"], row["sha256"], row["mime"])
    try:
        return path.read_bytes()
    except OSError:
        raise ApiError(404, "Fichier absent du serveur (dossier data/attachments incomplet). "
                            "Correctif : restaurez ce dossier depuis la sauvegarde.")
