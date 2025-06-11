# Image Evaluator Agent Setup Guide

## Environment Variables Required

### Required for Full Functionality

1. **Google Cloud Vision API** (for OCR text extraction):
   - Option 1: Service Account (Recommended)
     ```bash
     export GOOGLE_APPLICATION_CREDENTIALS="/path/to/your/service-account-key.json"
     ```
   - Option 2: API Key
     ```bash
     export GOOGLE_CLOUD_API_KEY="your-google-cloud-api-key"
     ```

   To get these credentials:
   1. Go to [Google Cloud Console](https://console.cloud.google.com/)
   2. Create a new project or select existing
   3. Enable the Cloud Vision API
   4. Create credentials (Service Account recommended)
   5. Download the JSON key file

### Optional Configuration

2. **Tesseract OCR** (local OCR alternative):
   ```bash
   # Install tesseract on your system first:
   # Ubuntu/Debian: sudo apt-get install tesseract-ocr
   # macOS: brew install tesseract
   # Then optionally set the path if not in system PATH:
   export TESSERACT_CMD="/usr/bin/tesseract"
   ```

3. **YOLO Models** (for object detection):
   - Models will be automatically downloaded on first use
   - No API key required

## Dependencies That Don't Require API Keys

The following dependencies work out of the box without configuration:
- `pillow` - Image processing
- `scikit-image` - Image analysis
- `opencv-python` - Computer vision operations
- `imagehash` - Perceptual hashing
- `ultralytics` - YOLO object detection (downloads models automatically)

## Testing the Agent

Once configured, test the agent with:

```bash
curl -X POST http://localhost:8000/api/v1/agents/image_evaluator/runs \
  -H "Content-Type: application/json" \
  -d '{
    "message": "evaluate https://example.com/cannabis-product.jpg",
    "stream": false
  }'
```

## Graceful Degradation

The agent is designed to work even without all dependencies:
- Without Google Cloud Vision: OCR features will be disabled
- Without pytesseract: Falls back to cloud OCR or disables text extraction
- Without opencv-python: Basic quality analysis still works via PIL
- Without YOLO: Basic object detection using shape analysis

## Production Recommendations

1. Use Google Cloud Service Account for better security and rate limits
2. Install tesseract locally for faster OCR without API calls
3. Consider caching image analysis results to reduce API costs
4. Monitor Google Cloud Vision API usage to stay within free tier or budget