"""Opaque artifact downloads that never expose local paths."""

from flask import current_app, request, send_file

from . import api


@api.get("/artifacts/<artifact_id>")
def get_artifact(artifact_id: str):
    repository = current_app.extensions["blotguard_repository"]
    storage = current_app.extensions["blotguard_storage"]
    artifact = repository.get_artifact(artifact_id)
    as_attachment = request.args.get("download", "").lower() in {
        "1",
        "true",
        "yes",
    }
    return send_file(
        storage.absolute(artifact["path"]),
        mimetype=artifact["media_type"],
        as_attachment=as_attachment,
        download_name=artifact["filename"],
        conditional=True,
    )
