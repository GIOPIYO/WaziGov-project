"""Phone image verification module for WaziGov.

Verifies phone images against three criteria:
1. Geolocation: EXIF GPS within reference site bounds
2. Authenticity: metadata integrity and basic deepfake detection
3. Scene Matching: keypoint matching against reference images

Returns a verification report per image with confidence scores.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

import cv2
import numpy as np
from PIL import Image
from PIL.ExifTags import TAGS


@dataclass(frozen=True)
class GPSCoords:
    latitude: float
    longitude: float
    altitude: Optional[float] = None

    def distance_to(self, other: GPSCoords) -> float:
        """Simple approximation: degrees to km (1 degree ~ 111 km)."""
        lat_diff = (self.latitude - other.latitude) * 111.0
        lon_diff = (self.longitude - other.longitude) * 111.0
        return float(np.sqrt(lat_diff**2 + lon_diff**2))

    def within_bounds(self, bounds: tuple[float, float, float, float]) -> bool:
        """Check if GPS is within lat_min, lon_min, lat_max, lon_max."""
        lat_min, lon_min, lat_max, lon_max = bounds
        return (lat_min <= self.latitude <= lat_max and
                lon_min <= self.longitude <= lon_max)


@dataclass(frozen=True)
class VerificationReport:
    image_path: str
    timestamp: str
    geolocation_score: float  # 0-1: GPS valid + within bounds
    authenticity_score: float  # 0-1: metadata integrity + not deepfake
    scene_match_score: float   # 0-1: keypoint matches to reference
    gps_coords: Optional[GPSCoords] = None
    metadata_issues: list[str] = None
    overall_status: str = "pass"  # pass, flag, review-needed
    creation_timestamp: Optional[str] = None
    metadata_stripped: bool = False
    timestamp_suspicious: bool = False
    verdict: str = "PASS"  # User-friendly: PASS, REVIEW, REJECT
    reasoning: list[str] = None

    def to_dict(self, include_gps: bool = True):
        d = asdict(self)
        if self.gps_coords and include_gps:
            d["gps_coords"] = {
                "latitude": self.gps_coords.latitude,
                "longitude": self.gps_coords.longitude,
                "altitude": self.gps_coords.altitude,
            }
        elif not include_gps:
            d["gps_coords"] = None  # Redact for privacy
        d["metadata_issues"] = self.metadata_issues or []
        d["reasoning"] = self.reasoning or []
        return d


def extract_exif(image_path: Path) -> dict:
    """Extract EXIF data from image."""
    try:
        img = Image.open(image_path)
        exif_data = img._getexif()
        if not exif_data:
            return {}
        
        result = {}
        for tag_id, value in exif_data.items():
            tag_name = TAGS.get(tag_id, tag_id)
            result[tag_name] = value
        return result
    except Exception as e:
        return {"error": str(e)}


def parse_gps_from_exif(exif_data: dict) -> Optional[GPSCoords]:
    """Parse GPS coordinates from EXIF."""
    try:
        if "GPSInfo" not in exif_data:
            return None
        
        gps_info = exif_data["GPSInfo"]
        lat = _dms_to_dd(gps_info[2])
        lon = _dms_to_dd(gps_info[4])
        alt = None
        if 6 in gps_info and gps_info[6]:
            alt = float(gps_info[6])
        
        return GPSCoords(latitude=lat, longitude=lon, altitude=alt)
    except (KeyError, IndexError, TypeError):
        return None


def _dms_to_dd(dms_data) -> float:
    """Convert DMS (degrees, minutes, seconds) tuple to decimal degrees."""
    try:
        degrees = float(dms_data[0])
        minutes = float(dms_data[1]) / 60.0
        seconds = float(dms_data[2]) / 3600.0
        return degrees + minutes + seconds
    except (TypeError, ZeroDivisionError, IndexError):
        return 0.0


def check_metadata_integrity(exif_data: dict, image_path: Path) -> tuple[float, list[str], bool]:
    """Check for metadata consistency and tampering signs.
    
    Returns: (integrity_score, issues_list, is_metadata_stripped)
    """
    issues = []
    score = 1.0
    metadata_stripped = False
    
    # Check if EXIF exists at all
    if not exif_data or "error" in exif_data:
        issues.append("No EXIF data found")
        metadata_stripped = True  # Likely stripped/laundered
        score = 0.3
    else:
        # Check for expected EXIF fields
        if "DateTime" not in exif_data:
            issues.append("Missing creation timestamp")
            score -= 0.1
        
        if "GPSInfo" not in exif_data:
            issues.append("No GPS data")
            score -= 0.15
        
        expected_fields = ["Model", "Orientation"]
        missing = [f for f in expected_fields if f not in exif_data]
        if missing:
            issues.append(f"Missing fields: {', '.join(missing)}")
            score -= 0.05
    
    score = max(0.0, min(1.0, score))
    return score, issues, metadata_stripped


def detect_deepfake_baseline(image_path: Path) -> float:
    """Lightweight deepfake detection using face detection + entropy check."""
    try:
        img = cv2.imread(str(image_path))
        if img is None:
            return 0.5
        
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Use OpenCV face cascade (simple baseline)
        face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        )
        faces = face_cascade.detectMultiScale(gray, 1.1, 4)
        
        # If no faces, assume it's not a deepfake (or just not a portrait)
        if len(faces) == 0:
            return 0.8  # Neutral: no face to check
        
        # Basic heuristic: check entropy of face regions
        face_entropies = []
        for (x, y, w, h) in faces:
            face_roi = gray[y:y+h, x:x+w]
            entropy = _compute_entropy(face_roi)
            face_entropies.append(entropy)
        
        # Deepfakes often have lower entropy in face regions (over-smoothed)
        avg_entropy = np.mean(face_entropies) if face_entropies else 0
        # Typical entropy for real faces: 6-7.5; deepfakes: 4-5.5
        deepfake_score = min(1.0, max(0.0, (avg_entropy - 4.0) / 3.5))
        
        return deepfake_score
    except Exception:
        return 0.7  # Neutral if detection fails


def extract_creation_timestamp(exif_data: dict) -> Optional[str]:
    """Extract creation timestamp from EXIF."""
    if "DateTime" in exif_data:
        return exif_data["DateTime"]
    if "DateTimeOriginal" in exif_data:
        return exif_data["DateTimeOriginal"]
    return None


def check_timestamp_suspicious(creation_ts: Optional[str], upload_ts: str, max_age_days: int = 30) -> tuple[bool, Optional[str]]:
    """Check if image creation time is suspiciously old relative to upload.
    
    Returns: (is_suspicious, reason)
    """
    if not creation_ts:
        return False, None
    
    try:
        # Parse timestamps (EXIF format: YYYY:MM:DD HH:MM:SS)
        exif_fmt = "%Y:%m:%d %H:%M:%S"
        iso_fmt = "%Y-%m-%dT%H:%M:%S.%f"
        
        created = datetime.strptime(creation_ts, exif_fmt)
        uploaded = datetime.fromisoformat(upload_ts.split(".")[0])
        
        age = uploaded - created
        if age.days > max_age_days:
            return True, f"Image is {age.days} days old (max allowed: {max_age_days} days)"
        
        if age.total_seconds() < 0:
            return True, "Image creation time is in the future (clock/timezone issue)"
        
        return False, None
    except (ValueError, TypeError):
        return False, None


def _compute_entropy(image: np.ndarray) -> float:
    """Compute Shannon entropy of an image."""
    hist, _ = np.histogram(image.flatten(), bins=256, range=(0, 256))
    hist = hist / hist.sum()
    hist = hist[hist > 0]
    entropy = -np.sum(hist * np.log2(hist))
    return entropy


def match_scene_keypoints(phone_image_path: Path, reference_image_path: Path) -> float:
    """Match keypoints between phone image and reference using ORB."""
    try:
        phone_img = cv2.imread(str(phone_image_path))
        ref_img = cv2.imread(str(reference_image_path))
        
        if phone_img is None or ref_img is None:
            return 0.0
        
        phone_gray = cv2.cvtColor(phone_img, cv2.COLOR_BGR2GRAY)
        ref_gray = cv2.cvtColor(ref_img, cv2.COLOR_BGR2GRAY)
        
        # Use ORB (faster and free, vs SIFT which requires opencv-contrib)
        orb = cv2.ORB_create(nfeatures=500)
        kp1, des1 = orb.detectAndCompute(phone_gray, None)
        kp2, des2 = orb.detectAndCompute(ref_gray, None)
        
        if des1 is None or des2 is None:
            return 0.0
        
        # BFMatcher for ORB
        bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
        matches = bf.match(des1, des2)
        matches = sorted(matches, key=lambda x: x.distance)
        
        # Score: ratio of good matches to total keypoints
        good_matches = [m for m in matches if m.distance < 50]
        max_kps = max(len(kp1), len(kp2))
        
        if max_kps == 0:
            return 0.0
        
        match_score = len(good_matches) / max_kps
        return float(min(1.0, match_score))
    except Exception:
        return 0.0


def verify_image(
    image_path: Path,
    reference_bounds: Optional[tuple[float, float, float, float]] = None,
    reference_image: Optional[Path] = None,
    upload_timestamp: Optional[str] = None,
    max_image_age_days: int = 30,
) -> VerificationReport:
    """Verify a single image against all criteria.
    
    Args:
        image_path: path to image file
        reference_bounds: (lat_min, lon_min, lat_max, lon_max) site bounds
        reference_image: path to reference satellite/photo
        upload_timestamp: ISO timestamp of upload (defaults to now)
        max_image_age_days: max allowed age of image relative to upload
    """
    image_path = Path(image_path)
    if upload_timestamp is None:
        upload_timestamp = datetime.utcnow().isoformat()
    
    # 1. Extract EXIF
    exif_data = extract_exif(image_path)
    gps = parse_gps_from_exif(exif_data)
    creation_ts = extract_creation_timestamp(exif_data)
    
    # 2. Geolocation score
    geolocation_score = 0.0
    if gps:
        if reference_bounds and gps.within_bounds(reference_bounds):
            geolocation_score = 1.0
        elif reference_bounds:
            geolocation_score = 0.3  # GPS exists but outside bounds
        else:
            geolocation_score = 0.7  # GPS exists but no reference bounds
    
    # 3. Authenticity score
    metadata_score, metadata_issues, metadata_stripped = check_metadata_integrity(exif_data, image_path)
    deepfake_score = detect_deepfake_baseline(image_path)
    authenticity_score = (metadata_score + deepfake_score) / 2.0
    
    # 4. Scene match score
    scene_match_score = 0.0
    if reference_image and Path(reference_image).exists():
        scene_match_score = match_scene_keypoints(image_path, Path(reference_image))
    
    # 5. Timestamp validation
    timestamp_suspicious, ts_reason = check_timestamp_suspicious(creation_ts, upload_timestamp, max_image_age_days)
    if ts_reason:
        metadata_issues.append(ts_reason)
    
    # 6. Compute user-friendly verdict and reasoning
    reasoning = []
    scores = [geolocation_score, authenticity_score, scene_match_score]
    avg_score = np.mean(scores)
    
    # Build reasoning
    if metadata_stripped:
        reasoning.append("⚠ All EXIF metadata removed (possible old/laundered photo)")
    if timestamp_suspicious:
        reasoning.append(f"⚠ {ts_reason}")
    if not gps:
        reasoning.append("⚠ No GPS coordinates found")
    elif reference_bounds and not gps.within_bounds(reference_bounds):
        reasoning.append(f"⚠ GPS location outside project site bounds")
    if deepfake_score < 0.6:
        reasoning.append("⚠ Image may contain synthetic content")
    if scene_match_score < 0.3 and reference_image:
        reasoning.append("⚠ Scene does not match reference image")
    if avg_score >= 0.75:
        status = "pass"
        verdict = "PASS"
        if not reasoning:
            reasoning.append("✓ All checks passed - image authentic and verified")
    elif avg_score >= 0.50:
        status = "review-needed"
        verdict = "REVIEW"
        if not reasoning:
            reasoning.append("Image requires manual review by moderator")
    else:
        status = "flag"
        verdict = "REJECT"
        if not reasoning:
            reasoning.append("Multiple verification checks failed")
    
    return VerificationReport(
        image_path=str(image_path),
        timestamp=upload_timestamp,
        geolocation_score=float(geolocation_score),
        authenticity_score=float(authenticity_score),
        scene_match_score=float(scene_match_score),
        gps_coords=gps,
        metadata_issues=metadata_issues,
        overall_status=status,
        creation_timestamp=creation_ts,
        metadata_stripped=metadata_stripped,
        timestamp_suspicious=timestamp_suspicious,
        verdict=verdict,
        reasoning=reasoning,
    )


def batch_verify(
    image_dir: Path,
    reference_bounds: Optional[tuple[float, float, float, float]] = None,
    reference_image: Optional[Path] = None,
    output_dir: Optional[Path] = None,
    privacy_mode: bool = False,
) -> list[VerificationReport]:
    """Verify all images in a directory.
    
    Args:
        image_dir: directory containing images
        reference_bounds: site geolocation bounds
        reference_image: reference satellite/photo
        output_dir: where to save reports
        privacy_mode: if True, redact GPS coordinates from reports
    """
    image_dir = Path(image_dir)
    output_dir = Path(output_dir) if output_dir else Path("outputs/phone_verification")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    reports = []
    for img_file in sorted(image_dir.glob("*.jpg")) + sorted(image_dir.glob("*.png")):
        print(f"Verifying {img_file.name}...")
        report = verify_image(img_file, reference_bounds, reference_image)
        reports.append(report)
    
    # Save batch report
    batch_report = {
        "timestamp": datetime.utcnow().isoformat(),
        "image_count": len(reports),
        "pass_count": sum(1 for r in reports if r.verdict == "PASS"),
        "review_count": sum(1 for r in reports if r.verdict == "REVIEW"),
        "reject_count": sum(1 for r in reports if r.verdict == "REJECT"),
        "avg_geolocation_score": float(np.mean([r.geolocation_score for r in reports])) if reports else 0,
        "avg_authenticity_score": float(np.mean([r.authenticity_score for r in reports])) if reports else 0,
        "avg_scene_match_score": float(np.mean([r.scene_match_score for r in reports])) if reports else 0,
        "images": [r.to_dict(include_gps=not privacy_mode) for r in reports],
    }
    
    report_path = output_dir / "phone_verification_report.json"
    with open(report_path, "w") as f:
        json.dump(batch_report, f, indent=2)
    print(f"\nVerification report saved to {report_path}")
    
    return reports


def create_smoke_dataset(output_dir: Path) -> tuple[Path, Path]:
    """Create synthetic phone images for testing."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Create a synthetic reference image (satellite-like)
    ref_img = np.random.randint(50, 200, (256, 256, 3), dtype=np.uint8)
    # Add some features (circles and rectangles to mimic buildings)
    cv2.circle(ref_img, (64, 64), 30, (100, 100, 150), -1)
    cv2.rectangle(ref_img, (150, 100), (220, 180), (120, 120, 100), -1)
    ref_path = output_dir / "reference_image.jpg"
    cv2.imwrite(str(ref_path), ref_img)
    
    # Create a synthetic phone image (similar but slightly different)
    phone_img = ref_img.copy()
    # Add some noise and slight rotation to simulate a real phone photo
    noise = np.random.normal(0, 10, phone_img.shape).astype(np.uint8)
    phone_img = cv2.add(phone_img, noise)
    phone_path = output_dir / "phone_image.jpg"
    cv2.imwrite(str(phone_path), phone_img)
    
    print(f"Smoke-test images created:")
    print(f"  Reference: {ref_path}")
    print(f"  Phone: {phone_path}")
    
    return ref_path, phone_path


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Verify phone images for geolocation, authenticity, and scene matching."
    )
    parser.add_argument(
        "--image-path",
        type=Path,
        help="Path to a single image to verify",
    )
    parser.add_argument(
        "--image-dir",
        type=Path,
        help="Directory containing images to verify",
    )
    parser.add_argument(
        "--reference-image",
        type=Path,
        help="Reference image for scene matching",
    )
    parser.add_argument(
        "--lat-min",
        type=float,
        help="Minimum latitude of site bounds",
    )
    parser.add_argument(
        "--lon-min",
        type=float,
        help="Minimum longitude of site bounds",
    )
    parser.add_argument(
        "--lat-max",
        type=float,
        help="Maximum latitude of site bounds",
    )
    parser.add_argument(
        "--lon-max",
        type=float,
        help="Maximum longitude of site bounds",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("outputs/phone_verification"),
        help="Output directory for reports",
    )
    parser.add_argument(
        "--max-image-age-days",
        type=int,
        default=30,
        help="Maximum allowed age of image relative to upload (default: 30)",
    )
    parser.add_argument(
        "--privacy-mode",
        action="store_true",
        help="Redact GPS coordinates from reports",
    )
    parser.add_argument(
        "--smoke-test",
        action="store_true",
        help="Run synthetic smoke test",
    )
    return parser


def main():
    parser = build_arg_parser()
    args = parser.parse_args()
    
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    if args.smoke_test:
        print("Running phone-image verification smoke test...")
        smoke_dir = output_dir / "smoke_data"
        ref_path, phone_path = create_smoke_dataset(smoke_dir)
        
        report = verify_image(phone_path, reference_image=ref_path)
        
        print("\nSmoke-test verification result:")
        print(f"  Verdict: {report.verdict}")
        print(f"  Geolocation Score: {report.geolocation_score:.2f}")
        print(f"  Authenticity Score: {report.authenticity_score:.2f}")
        print(f"  Scene Match Score: {report.scene_match_score:.2f}")
        print(f"  Reasoning:")
        for reason in report.reasoning:
            print(f"    {reason}")
        
        report_path = output_dir / "phone_verification_report.json"
        with open(report_path, "w") as f:
            json.dump(report.to_dict(include_gps=not args.privacy_mode), f, indent=2)
        print(f"\nSmoke-test report saved to {report_path}")
        return
    
    # Build reference bounds if provided
    reference_bounds = None
    if all(getattr(args, f) is not None for f in ["lat_min", "lon_min", "lat_max", "lon_max"]):
        reference_bounds = (args.lat_min, args.lon_min, args.lat_max, args.lon_max)
        print(f"Reference bounds: lat=[{args.lat_min}, {args.lat_max}], lon=[{args.lon_min}, {args.lon_max}]")
    
    if args.privacy_mode:
        print("Privacy mode enabled: GPS coordinates will be redacted from reports.")
    
    # Single image
    if args.image_path:
        report = verify_image(
            args.image_path,
            reference_bounds,
            args.reference_image,
            max_image_age_days=args.max_image_age_days,
        )
        print(f"\nVerification report for {args.image_path}:")
        print(f"  Verdict: {report.verdict}")
        print(f"  Geolocation Score: {report.geolocation_score:.2f}")
        print(f"  Authenticity Score: {report.authenticity_score:.2f}")
        print(f"  Scene Match Score: {report.scene_match_score:.2f}")
        print(f"  Reasoning:")
        for reason in report.reasoning:
            print(f"    {reason}")
        
        report_path = output_dir / f"{args.image_path.stem}_verification.json"
        with open(report_path, "w") as f:
            json.dump(report.to_dict(include_gps=not args.privacy_mode), f, indent=2)
        print(f"\nReport saved to {report_path}")
        return
    
    # Batch directory
    if args.image_dir:
        batch_verify(
            args.image_dir,
            reference_bounds,
            args.reference_image,
            output_dir,
            privacy_mode=args.privacy_mode,
        )
        return
    
    print("Please provide --image-path, --image-dir, or --smoke-test")
    sys.exit(1)


if __name__ == "__main__":
    main()
