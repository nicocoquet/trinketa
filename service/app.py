from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
import time
from dataclasses import dataclass
from io import BytesIO
from pathlib import PurePath
from typing import Any
from urllib.parse import quote, urlencode, urlparse

import httpx
from fastapi import Depends, FastAPI, Header, HTTPException, Query, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from PIL import Image, ImageOps, UnidentifiedImageError
from pillow_heif import register_heif_opener

register_heif_opener()
Image.MAX_IMAGE_PIXELS = 60_000_000

GITHUB_API = "https://api.github.com"
GITHUB_ACCEPT = "application/vnd.github+json"
UPLOAD_PATH = "photos/bibliotheque/isbn/a_traiter"
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".heic", ".heif"}
MAX_FILES = 10
MAX_FILE_SIZE = 15 * 1024 * 1024
MAX_BATCH_SIZE = 50 * 1024 * 1024


@dataclass(frozen=True)
class Settings:
    github_client_id: str
    github_client_secret: str
    session_secret: str
    repository: str = "nicocoquet/trinketa"
    pages_url: str = "https://nicocoquet.github.io/trinketa/depot-isbn/"
    allowed_users: tuple[str, ...] = ("nicocoquet",)

    @classmethod
    def from_environment(cls) -> "Settings":
        session_secret = os.getenv("SESSION_SECRET", "")
        if not session_secret:
            raise RuntimeError("Variable d’environnement manquante : SESSION_SECRET")
        users = tuple(item.strip().casefold() for item in os.getenv("ALLOWED_USERS", "nicocoquet").split(",") if item.strip())
        return cls(
            github_client_id=os.getenv("GITHUB_CLIENT_ID", ""),
            github_client_secret=os.getenv("GITHUB_CLIENT_SECRET", ""),
            session_secret=session_secret,
            repository=os.getenv("GITHUB_REPOSITORY", "nicocoquet/trinketa"),
            pages_url=os.getenv("PAGES_URL", "https://nicocoquet.github.io/trinketa/depot-isbn/"),
            allowed_users=users,
        )


class UploadFile(BaseModel):
    filename: str
    content: str


class UploadRequest(BaseModel):
    files: list[UploadFile]


class SessionStore:
    def __init__(self, lifetime: int = 8 * 60 * 60) -> None:
        self.lifetime = lifetime
        self._sessions: dict[str, dict[str, Any]] = {}

    def create(self, login: str, token: str, permission: str) -> str:
        self.purge()
        key = secrets.token_urlsafe(32)
        self._sessions[key] = {"login": login, "github_token": token, "permission": permission, "expires": int(time.time()) + self.lifetime}
        return key

    def get(self, key: str) -> dict[str, Any] | None:
        session = self._sessions.get(key)
        if not session or session["expires"] <= time.time():
            self._sessions.pop(key, None)
            return None
        return session

    def delete(self, key: str) -> None:
        self._sessions.pop(key, None)

    def purge(self) -> None:
        now = time.time()
        for key in [key for key, value in self._sessions.items() if value["expires"] <= now]:
            self._sessions.pop(key, None)


def _urlsafe_encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _urlsafe_decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def sign_payload(payload: dict[str, Any], secret: str) -> str:
    body = _urlsafe_encode(json.dumps(payload, separators=(",", ":")).encode())
    signature = _urlsafe_encode(hmac.new(secret.encode(), body.encode(), hashlib.sha256).digest())
    return f"{body}.{signature}"


def verify_payload(value: str, secret: str) -> dict[str, Any]:
    try:
        body, provided = value.rsplit(".", 1)
        expected = _urlsafe_encode(hmac.new(secret.encode(), body.encode(), hashlib.sha256).digest())
        if not hmac.compare_digest(provided, expected):
            raise ValueError
        payload = json.loads(_urlsafe_decode(body))
        if int(payload["exp"]) <= time.time():
            raise ValueError
        return payload
    except (ValueError, KeyError, TypeError, json.JSONDecodeError) as error:
        raise HTTPException(status_code=400, detail="Jeton invalide ou expiré.") from error


def allowed_return_url(candidate: str, pages_url: str) -> str:
    wanted, allowed = urlparse(candidate), urlparse(pages_url)
    if (wanted.scheme, wanted.netloc, wanted.path) != (allowed.scheme, allowed.netloc, allowed.path):
        return pages_url
    return candidate.split("#", 1)[0]


def safe_filename(filename: str) -> str:
    name = PurePath(filename).name
    if name != filename or not name or any(ord(char) < 32 for char in name):
        raise HTTPException(status_code=400, detail="Nom de fichier invalide.")
    if PurePath(name).suffix.casefold() not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"Format non accepté pour {name}.")
    return name


def validate_image(name: str, content: bytes) -> None:
    suffix = PurePath(name).suffix.casefold()
    valid = (
        (suffix in {".jpg", ".jpeg"} and content.startswith(b"\xff\xd8\xff"))
        or (suffix == ".png" and content.startswith(b"\x89PNG\r\n\x1a\n"))
        or (suffix == ".webp" and content[:4] == b"RIFF" and content[8:12] == b"WEBP")
        or (suffix in {".heic", ".heif"} and len(content) >= 12 and content[4:8] == b"ftyp")
    )
    if not valid:
        raise HTTPException(status_code=400, detail=f"{name} ne correspond pas à un fichier image valide.")


def normalize_to_jpeg(name: str, content: bytes) -> tuple[str, bytes]:
    """Normalise l’image et supprime toutes ses métadonnées avant GitHub."""
    try:
        with Image.open(BytesIO(content)) as source:
            source.load()
            image = ImageOps.exif_transpose(source)
            if image.mode in {"RGBA", "LA"} or (image.mode == "P" and "transparency" in image.info):
                rgba = image.convert("RGBA")
                background = Image.new("RGB", rgba.size, "white")
                background.paste(rgba, mask=rgba.getchannel("A"))
                image = background
            else:
                image = image.convert("RGB")
            image.thumbnail((3200, 3200), Image.Resampling.LANCZOS)
            output = BytesIO()
            image.save(output, format="JPEG", quality=92, optimize=True, progressive=True)
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError) as error:
        raise HTTPException(status_code=400, detail=f"Conversion impossible pour {name}.") from error
    return f"{PurePath(name).stem}.jpg", output.getvalue()


async def github_request(method: str, path: str, token: str | None = None, allow_404: bool = False, **kwargs: Any) -> Any:
    headers = {"Accept": GITHUB_ACCEPT, "X-GitHub-Api-Version": "2026-03-10"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    async with httpx.AsyncClient(timeout=45) as client:
        response = await client.request(method, f"{GITHUB_API}{path}", headers=headers, **kwargs)
    if allow_404 and response.status_code == 404:
        return None
    if response.status_code >= 400:
        try:
            message = response.json().get("message", "Erreur GitHub")
        except ValueError:
            message = "Erreur GitHub"
        raise HTTPException(status_code=response.status_code, detail=message)
    return response.json() if response.content else None


async def repository_permission(repository: str, login: str, token: str) -> str:
    owner, repo = repository.split("/", 1)
    result = await github_request("GET", f"/repos/{owner}/{repo}/collaborators/{quote(login)}/permission", token)
    permission = result.get("permission", "none")
    if permission not in {"admin", "maintain", "write", "push"}:
        raise HTTPException(status_code=403, detail="Ce compte ne possède pas le droit d’écriture sur le dépôt.")
    return permission


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings.from_environment()
    sessions = SessionStore()
    owner, repo = settings.repository.split("/", 1)
    app = FastAPI(title="Dépôt ISBN Trinketa", docs_url=None, redoc_url=None)
    origin = urlparse(settings.pages_url)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[f"{origin.scheme}://{origin.netloc}"],
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["Authorization", "Content-Type"],
    )

    def current_session(authorization: str = Header(default="")) -> tuple[str, dict[str, Any]]:
        if not authorization.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Connexion GitHub requise.")
        key = authorization.removeprefix("Bearer ").strip()
        session = sessions.get(key)
        if not session:
            raise HTTPException(status_code=401, detail="Session expirée. Reconnectez-vous avec GitHub.")
        return key, session

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/auth/github")
    async def login(returnTo: str = Query(default="")) -> RedirectResponse:  # noqa: N803
        if not settings.github_client_id or not settings.github_client_secret:
            raise HTTPException(status_code=503, detail="La connexion GitHub n’est pas encore configurée.")
        destination = allowed_return_url(returnTo or settings.pages_url, settings.pages_url)
        state = sign_payload({"returnTo": destination, "exp": int(time.time()) + 600}, settings.session_secret)
        return RedirectResponse("https://github.com/login/oauth/authorize?" + urlencode({"client_id": settings.github_client_id, "state": state}))

    @app.get("/auth/callback")
    async def callback(code: str, state: str) -> RedirectResponse:
        state_payload = verify_payload(state, settings.session_secret)
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                "https://github.com/login/oauth/access_token",
                headers={"Accept": "application/json"},
                data={"client_id": settings.github_client_id, "client_secret": settings.github_client_secret, "code": code},
            )
        token = response.json().get("access_token")
        if not token:
            raise HTTPException(status_code=401, detail="GitHub n’a pas autorisé la connexion.")
        user = await github_request("GET", "/user", token)
        login_name = user["login"]
        if login_name.casefold() not in settings.allowed_users:
            raise HTTPException(status_code=403, detail="Ce compte GitHub n’est pas autorisé.")
        permission = await repository_permission(settings.repository, login_name, token)
        session_key = sessions.create(login_name, token, permission)
        return RedirectResponse(f"{state_payload['returnTo']}#session={session_key}")

    @app.get("/auth/session")
    async def session(data: tuple[str, dict[str, Any]] = Depends(current_session)) -> dict[str, Any]:
        return {"user": {"login": data[1]["login"], "permission": data[1]["permission"]}}

    @app.post("/auth/logout", status_code=204, response_class=Response)
    async def logout(data: tuple[str, dict[str, Any]] = Depends(current_session)) -> Response:
        sessions.delete(data[0])
        return Response(status_code=204)

    @app.get("/api/queue")
    async def queue(data: tuple[str, dict[str, Any]] = Depends(current_session)) -> dict[str, Any]:
        content = await github_request("GET", f"/repos/{owner}/{repo}/contents/{UPLOAD_PATH}?ref=main", data[1]["github_token"], allow_404=True)
        files = [item["name"] for item in content or [] if item.get("type") == "file" and item["name"] != ".gitkeep"]
        return {"count": len(files), "files": sorted(files)}

    @app.post("/api/uploads")
    async def upload(batch: UploadRequest, data: tuple[str, dict[str, Any]] = Depends(current_session)) -> dict[str, Any]:
        if not 1 <= len(batch.files) <= MAX_FILES:
            raise HTTPException(status_code=400, detail=f"Déposez entre 1 et {MAX_FILES} images par envoi.")
        decoded: list[tuple[str, bytes]] = []
        names: set[str] = set()
        total = 0
        for upload_file in batch.files:
            name = safe_filename(upload_file.filename)
            if name.casefold() in names:
                raise HTTPException(status_code=400, detail=f"Le fichier {name} est présent deux fois.")
            names.add(name.casefold())
            try:
                content = base64.b64decode(upload_file.content, validate=True)
            except ValueError as error:
                raise HTTPException(status_code=400, detail=f"Contenu invalide pour {name}.") from error
            if not content or len(content) > MAX_FILE_SIZE:
                raise HTTPException(status_code=400, detail=f"{name} doit peser entre 1 octet et 15 Mo.")
            validate_image(name, content)
            jpeg_name, jpeg_content = normalize_to_jpeg(name, content)
            if jpeg_name.casefold() in {existing_name.casefold() for existing_name, _ in decoded}:
                raise HTTPException(status_code=400, detail=f"Plusieurs images produiraient le nom {jpeg_name}.")
            total += len(jpeg_content)
            decoded.append((jpeg_name, jpeg_content))
        if total > MAX_BATCH_SIZE:
            raise HTTPException(status_code=400, detail="L’envoi complet dépasse 50 Mo.")

        for name, _ in decoded:
            path = f"{UPLOAD_PATH}/{name}"
            if await github_request("GET", f"/repos/{owner}/{repo}/contents/{quote(path, safe='/')}?ref=main", data[1]["github_token"], allow_404=True):
                raise HTTPException(status_code=409, detail=f"Un fichier nommé {name} existe déjà dans la file.")

        base_ref = await github_request("GET", f"/repos/{owner}/{repo}/git/ref/heads/main", data[1]["github_token"])
        base_sha = base_ref["object"]["sha"]
        base_commit = await github_request("GET", f"/repos/{owner}/{repo}/git/commits/{base_sha}", data[1]["github_token"])
        tree_entries = []
        for name, content in decoded:
            blob = await github_request("POST", f"/repos/{owner}/{repo}/git/blobs", data[1]["github_token"], json={"content": base64.b64encode(content).decode(), "encoding": "base64"})
            tree_entries.append({"path": f"{UPLOAD_PATH}/{name}", "mode": "100644", "type": "blob", "sha": blob["sha"]})
        tree = await github_request("POST", f"/repos/{owner}/{repo}/git/trees", data[1]["github_token"], json={"base_tree": base_commit["tree"]["sha"], "tree": tree_entries})
        commit = await github_request("POST", f"/repos/{owner}/{repo}/git/commits", data[1]["github_token"], json={"message": f"ISBN : déposer {len(decoded)} photographie(s)", "tree": tree["sha"], "parents": [base_sha]})
        branch = f"isbn-upload/{int(time.time())}-{secrets.token_hex(3)}"
        await github_request("POST", f"/repos/{owner}/{repo}/git/refs", data[1]["github_token"], json={"ref": f"refs/heads/{branch}", "sha": commit["sha"]})
        pull = await github_request("POST", f"/repos/{owner}/{repo}/pulls", data[1]["github_token"], json={
            "title": f"ISBN : déposer {len(decoded)} photographie(s)", "head": branch, "base": "main",
            "body": "Photographies déposées depuis l’interface Trinketa dans `photos/bibliotheque/isbn/a_traiter/`. Leur fusion alimente la file d’analyse ISBN.",
        })
        return {"pullRequest": {"number": pull["number"], "url": pull["html_url"]}, "files": [name for name, _ in decoded]}

    @app.post("/api/analysis")
    async def analysis(data: tuple[str, dict[str, Any]] = Depends(current_session)) -> dict[str, str]:
        await github_request(
            "POST", f"/repos/{owner}/{repo}/actions/workflows/analyse-isbn.yml/dispatches", data[1]["github_token"],
            json={"ref": "main", "inputs": {"limit": "25"}},
        )
        return {"status": "queued", "actionsUrl": f"https://github.com/{settings.repository}/actions/workflows/analyse-isbn.yml"}

    return app
