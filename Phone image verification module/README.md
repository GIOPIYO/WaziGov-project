# Phone Image Verification Module

Verifies phone images uploaded by citizens to the WaziGov platform for evidence authenticity. Prevents propaganda and ensures project evidence cannot be easily faked or laundered.

Validation across three criteria:

1. **Geolocation Verification** – Extract GPS from EXIF and validate within site bounds
2. **Authenticity & Forensics** – Check metadata integrity and basic deepfake detection
3. **Scene Matching** – Compare keypoints against reference satellite/reference images

## Features

✅ **EXIF & Geolocation** – GPS validation, site boundary checking  
✅ **Authenticity & Forensics** – Metadata integrity, deepfake detection (entropy-based face analysis)  
✅ **Scene Matching** – ORB keypoint matching against reference images  
✅ **Timestamp Validation** – Flag retroactively uploaded or suspiciously old images  
✅ **Metadata Stripping Detection** – Warn when all EXIF is missing (likely laundered photo)  
✅ **Privacy Mode** – Redact GPS from reports for citizen safety  
✅ **User-Friendly Verdicts** – Simple PASS/REVIEW/REJECT with reasoning  
✅ **REST API** – Flask server for platform integration  
✅ **Batch Processing** – Verify multiple images in one call  

## Quick Start

### CLI Mode

Run the synthetic smoke test first:

```powershell
python phone_image_verifier.py --smoke-test
```

Verify a single image with geolocation bounds:

```powershell
python phone_image_verifier.py `
  --image-path my_photo.jpg `
  --lat-min -1.3 --lon-min 36.7 --lat-max -1.2 --lon-max 36.8 `
  --reference-image satellite_reference.jpg
```

Batch verify all images in a directory:

```powershell
python phone_image_verifier.py `
  --image-dir ./photos `
  --lat-min -1.3 --lon-min 36.7 --lat-max -1.2 --lon-max 36.8 `
  --reference-image satellite_reference.jpg `
  --max-image-age-days 30 `
  --privacy-mode
```

### REST API Mode

Start the Flask server:

```powershell
python api_server.py
```

Server runs on `http://localhost:5000`.

**Configure site bounds:**

```bash
curl -X POST http://localhost:5000/config \
  -H "Content-Type: application/json" \
  -d '{
    "bounds": {
      "lat_min": -1.3,
      "lon_min": 36.7,
      "lat_max": -1.2,
      "lon_max": 36.8
    },
    "reference_image_path": "/path/to/satellite_ref.jpg"
  }'
```

**Upload and verify a single image:**

```bash
curl -X POST http://localhost:5000/verify \
  -F "file=@photo.jpg" \
  -F "privacy_mode=true" \
  -F "max_image_age_days=30"
```

Response:
```json
{
  "verdict": "PASS",
  "scores": {
    "geolocation": 1.0,
    "authenticity": 0.75,
    "scene_match": 0.65
  },
  "reasoning": [
    "✓ All checks passed - image authentic and verified"
  ],
  "report": {...}
}
```

**Batch verify a directory:**

```bash
curl -X POST http://localhost:5000/batch \
  -H "Content-Type: application/json" \
  -d '{
    "image_dir": "/path/to/photos",
    "privacy_mode": true
  }'
```

## Output

### Verdicts

- **PASS** – Image passes all checks (average score ≥ 0.75)
- **REVIEW** – Image requires manual moderator review (0.50–0.75)
- **REJECT** – Image fails multiple checks (< 0.50)

### Report Format

Each image generates:

```json
{
  "image_path": "photo.jpg",
  "timestamp": "2026-05-15T10:30:00.000000",
  "verdict": "PASS",
  "overall_status": "pass",
  "geolocation_score": 1.0,
  "authenticity_score": 0.75,
  "scene_match_score": 0.65,
  "gps_coords": {
    "latitude": -1.25,
    "longitude": 36.75,
    "altitude": 1500.0
  },
  "creation_timestamp": "2026-05-15 10:20:00",
  "metadata_stripped": false,
  "timestamp_suspicious": false,
  "reasoning": [
    "✓ All checks passed - image authentic and verified"
  ],
  "metadata_issues": []
}
```

(GPS redacted if `--privacy-mode` or `privacy_mode=true`)

## CLI Arguments

```
--image-path PATH           Single image to verify
--image-dir DIR             Directory of images to verify
--reference-image PATH      Reference satellite/photo for scene matching
--lat-min FLOAT             Site boundary: min latitude
--lon-min FLOAT             Site boundary: min longitude
--lat-max FLOAT             Site boundary: max latitude
--lon-max FLOAT             Site boundary: max longitude
--max-image-age-days INT    Max allowed image age (default: 30)
--privacy-mode              Redact GPS coordinates from reports
--output-dir DIR            Output directory for reports (default: outputs/phone_verification)
--smoke-test                Run synthetic test
```

## Methodology

### 1. Geolocation
- Extracts GPS coordinates from image EXIF metadata
- Validates against reference site bounds (latitude/longitude)
- **Score**: 
  - 1.0 if GPS within bounds
  - 0.3 if GPS exists but outside bounds
  - 0.7 if GPS exists but no bounds provided
  - 0.0 if no GPS found

### 2. Authenticity & Forensics
- **Metadata Integrity**:
  - Checks for EXIF data, creation timestamp, GPS, camera model
  - Flags metadata stripping (all fields missing)
  - Score: 1.0 if complete; reduced for missing fields
- **Deepfake Detection**:
  - Lightweight baseline using Haar face cascade + entropy analysis
  - Compares entropy of face regions (real: 6–7.5, deepfake: 4–5.5)
  - Scores smoothness/artificiality of synthetic content
- **Combined Score**: Average of metadata integrity and deepfake confidence

### 3. Scene Matching
- Uses OpenCV ORB (Oriented FAST and Rotated BRIEF) for keypoint detection
- Matches phone image keypoints against reference (satellite or reference photo)
- **Score**: Ratio of successful matches to total keypoints detected
- Enables verification that photo matches claimed location

### 4. Timestamp Validation
- Extracts creation timestamp from EXIF
- Flags images older than `--max-image-age-days` (default 30 days)
- Detects future-dated photos (clock/timezone issues)
- Indicates when image is retroactively uploaded

### 5. Metadata Stripping Detection
- Flags images with no EXIF data (score reduced to 0.3)
- Indicates possible old/laundered photos from third-party sources
- Reasoning: Recent smartphone photos always have EXIF; missing EXIF suggests reuse

## Limitations & Future Work

- **Deepfake detection** is a lightweight baseline; production should use SOTA detectors (e.g., MediaPipe Face Guard, Xception-based detectors, or API services like Truepic)
- **Scene matching** assumes reference image is from same viewpoint; fails under extreme angle/zoom changes
- **GPS spoofing** is not detected; recommend secondary verification (IP geolocation, cellular tower data)
- **Metadata stripping** is easy; future: hash-based integrity verification, blockchain anchoring
- No **weather/cloud handling**; overcast conditions may reduce scene-matching confidence
- No **account reputation tracking**; future: build uploader trust scores based on past uploads

## Integration with WaziGov Platform

1. Deploy `api_server.py` on your platform backend
2. Configure site bounds and reference image via POST `/config`
3. Citizens upload photos → POST `/verify` endpoint
4. Store verdicts and reasoning with submissions
5. Queue REVIEW/REJECT images for moderator inspection
6. Track uploader reputation based on PASS rate

## Privacy & Ethics

- **Privacy Mode** redacts GPS from stored reports
- Consider: What happens to rejected uploads? (Delete after review period?)
- Transparent communication: citizens should know images are automatically scanned
- Consider: Can GPS redaction be done client-side before upload?
- GDPR/data retention: set automatic expiration on upload files and reports

## Dependencies

- `numpy` – numerical operations
- `Pillow` – image I/O and EXIF extraction
- `opencv-python` – keypoint detection and scene matching
- `Flask` – REST API server
- `Flask-CORS` – Cross-Origin Resource Sharing
- `python-dotenv` – environment variable management

