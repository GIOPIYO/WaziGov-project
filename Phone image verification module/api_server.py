"""Flask REST API server for phone image verification.

Exposes endpoints for citizen upload platform integration.
Handles single image uploads and batch verification.
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

from flask import Flask, jsonify, request
from flask_cors import CORS
from werkzeug.utils import secure_filename

from phone_image_verifier import (
    verify_image,
    batch_verify,
    VerificationReport,
)

app = Flask(__name__)
CORS(app)

# Configuration
UPLOAD_DIR = Path("uploads")
OUTPUT_DIR = Path("outputs/phone_verification_api")
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png"}

# Create directories
UPLOAD_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Default reference bounds (can be overridden per request)
DEFAULT_BOUNDS = None  # (-1.3, 36.7, -1.2, 36.8)

# Store reference images globally
REFERENCE_IMAGE = None


def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route("/health", methods=["GET"])
def health():
    """Health check endpoint."""
    return jsonify({"status": "ok", "service": "phone-image-verification"}), 200


@app.route("/config", methods=["GET"])
def get_config():
    """Return server configuration."""
    return jsonify({
        "max_file_size_mb": MAX_FILE_SIZE / (1024 * 1024),
        "allowed_extensions": list(ALLOWED_EXTENSIONS),
        "default_bounds": DEFAULT_BOUNDS,
        "reference_image_set": REFERENCE_IMAGE is not None,
    }), 200


@app.route("/config", methods=["POST"])
def set_config():
    """Configure reference bounds and image."""
    global DEFAULT_BOUNDS, REFERENCE_IMAGE
    
    data = request.json or {}
    
    if "bounds" in data:
        bounds = data["bounds"]
        if isinstance(bounds, dict):
            DEFAULT_BOUNDS = (
                bounds.get("lat_min"),
                bounds.get("lon_min"),
                bounds.get("lat_max"),
                bounds.get("lon_max"),
            )
        elif isinstance(bounds, (list, tuple)) and len(bounds) == 4:
            DEFAULT_BOUNDS = tuple(bounds)
    
    if "reference_image_path" in data:
        ref_path = Path(data["reference_image_path"])
        if ref_path.exists():
            REFERENCE_IMAGE = ref_path
            return jsonify({"status": "ok", "reference_image": str(REFERENCE_IMAGE)}), 200
        else:
            return jsonify({"error": f"Reference image not found: {ref_path}"}), 404
    
    return jsonify({
        "status": "ok",
        "bounds": DEFAULT_BOUNDS,
        "reference_image": str(REFERENCE_IMAGE) if REFERENCE_IMAGE else None,
    }), 200


@app.route("/verify", methods=["POST"])
def verify_single():
    """Verify a single uploaded image.
    
    Request:
        - file: image file (multipart)
        - bounds (optional): {"lat_min", "lon_min", "lat_max", "lon_max"}
        - reference_image_path (optional): path to reference image
        - privacy_mode (optional): bool, redact GPS
        - max_image_age_days (optional): int, max age in days
    
    Response:
        {
            "verdict": "PASS" | "REVIEW" | "REJECT",
            "scores": {
                "geolocation": float,
                "authenticity": float,
                "scene_match": float
            },
            "reasoning": [str],
            "report": {...full VerificationReport...}
        }
    """
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400
    
    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "No file selected"}), 400
    
    if not allowed_file(file.filename):
        return jsonify({"error": f"File type not allowed. Allowed: {ALLOWED_EXTENSIONS}"}), 400
    
    # Save uploaded file
    filename = secure_filename(file.filename)
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S_")
    filepath = UPLOAD_DIR / (timestamp + filename)
    file.save(filepath)
    
    try:
        # Parse request parameters
        data = request.form or {}
        bounds = None
        if "bounds" in data:
            try:
                bounds_dict = json.loads(data["bounds"])
                bounds = (
                    bounds_dict.get("lat_min"),
                    bounds_dict.get("lon_min"),
                    bounds_dict.get("lat_max"),
                    bounds_dict.get("lon_max"),
                )
            except json.JSONDecodeError:
                pass
        bounds = bounds or DEFAULT_BOUNDS

        ref_image = data.get("reference_image_path") or REFERENCE_IMAGE
        privacy_mode = data.get("privacy_mode", "").lower() in {"true", "1", "yes"}
        max_age = int(data.get("max_image_age_days", 30))

        # Client-supplied GPS fallback: accept JSON list/string or separate lat/lon fields
        client_gps = None
        if "client_gps" in data:
            try:
                client_gps = json.loads(data["client_gps"])
                if isinstance(client_gps, dict):
                    client_gps = (client_gps.get("lat"), client_gps.get("lon"))
            except Exception:
                # try to parse simple comma-separated
                try:
                    parts = data["client_gps"].split(",")
                    client_gps = (float(parts[0]), float(parts[1]))
                except Exception:
                    client_gps = None
        else:
            # fallback to client_lat/client_lon fields
            try:
                if data.get("client_lat") and data.get("client_lon"):
                    client_gps = (float(data.get("client_lat")), float(data.get("client_lon")))
            except Exception:
                client_gps = None

        # Optional upload timestamp provided by client (ISO format). If not provided server uses now.
        upload_ts = data.get("upload_timestamp") or datetime.utcnow().isoformat()

        # Verify
        report = verify_image(
            filepath,
            reference_bounds=bounds,
            reference_image=ref_image,
            upload_timestamp=upload_ts,
            max_image_age_days=max_age,
            client_gps=client_gps,
        )
        
        return jsonify({
            "verdict": report.verdict,
            "scores": {
                "geolocation": report.geolocation_score,
                "authenticity": report.authenticity_score,
                "scene_match": report.scene_match_score,
            },
            "reasoning": report.reasoning,
            "report": report.to_dict(include_gps=not privacy_mode),
        }), 200
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/batch", methods=["POST"])
def batch_verify_endpoint():
    """Verify multiple images in a directory.
    
    Request:
        - image_dir: path to directory with images
        - bounds (optional): {"lat_min", "lon_min", "lat_max", "lon_max"}
        - reference_image_path (optional): path to reference image
        - privacy_mode (optional): bool
    
    Response:
        {
            "image_count": int,
            "pass_count": int,
            "review_count": int,
            "reject_count": int,
            "summary": {...},
            "reports": [...]
        }
    """
    data = request.json or {}
    image_dir = data.get("image_dir")
    
    if not image_dir:
        return jsonify({"error": "image_dir required"}), 400
    
    image_dir = Path(image_dir)
    if not image_dir.exists():
        return jsonify({"error": f"Directory not found: {image_dir}"}), 404
    
    try:
        bounds = None
        if "bounds" in data:
            bounds_dict = data["bounds"]
            bounds = (
                bounds_dict.get("lat_min"),
                bounds_dict.get("lon_min"),
                bounds_dict.get("lat_max"),
                bounds_dict.get("lon_max"),
            )
        bounds = bounds or DEFAULT_BOUNDS
        
        ref_image = data.get("reference_image_path") or REFERENCE_IMAGE
        privacy_mode = data.get("privacy_mode", False)
        
        reports = batch_verify(
            image_dir,
            reference_bounds=bounds,
            reference_image=ref_image,
            output_dir=OUTPUT_DIR,
            privacy_mode=privacy_mode,
        )
        
        return jsonify({
            "image_count": len(reports),
            "pass_count": sum(1 for r in reports if r.verdict == "PASS"),
            "review_count": sum(1 for r in reports if r.verdict == "REVIEW"),
            "reject_count": sum(1 for r in reports if r.verdict == "REJECT"),
            "summary": {
                "avg_geolocation_score": sum(r.geolocation_score for r in reports) / len(reports) if reports else 0,
                "avg_authenticity_score": sum(r.authenticity_score for r in reports) / len(reports) if reports else 0,
                "avg_scene_match_score": sum(r.scene_match_score for r in reports) / len(reports) if reports else 0,
            },
            "reports": [r.to_dict(include_gps=not privacy_mode) for r in reports],
        }), 200
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "false").lower() in {"true", "1"}
    app.run(host="0.0.0.0", port=port, debug=debug)
