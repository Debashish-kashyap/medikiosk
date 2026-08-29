# Audio Input Fixes - Root Cause Analysis

## Issues Found and Fixed

### 1. **Critical: Missing `asrStatus()` API method** (api.js)
**Location:** `frontend/src/api.js`
**Issue:** The `asrStatus()` function was missing from the API client, but VoiceButton was calling it on mount to detect server ASR availability.
**Impact:** Frontend couldn't check if server-side Whisper ASR was available, breaking the fallback to MediaRecorder recording.
**Fix:** Added `asrStatus: () => req("/api/asr/status")` to the api export.

---

### 2. **Critical: Function Hoisting Issue** (api.js)
**Location:** `frontend/src/api.js` lines 6-12, 67
**Issue:** The `blobFilename()` helper function was defined at the END of the file (after the api export), but was being called in `transcribeAudio()` which happens earlier in execution.
**Impact:** When sending audio blobs, the filename would be `undefined`, breaking the backend's audio format detection.
**Fix:** Moved `blobFilename()` function to the TOP of the file (lines 6-12), before the api export uses it.

---

### 3. **Critical: Wrong Variable Reference** (VoiceButton.jsx)
**Location:** `frontend/src/components/VoiceButton.jsx` lines 291-293
**Issue:** Error handling in `startServerCapture()` used `lang` instead of `langRef.current`:
```javascript
// WRONG:
setErrorMsg(t(lang, "micPermissionDenied"));

// CORRECT:
setErrorMsg(t(langRef.current, "micPermissionDenied"));
```
**Impact:** ReferenceError thrown when microphone permission denied, preventing proper error display and breaking audio input flow.
**Fix:** Changed all three instances to use `langRef.current`.

---

### 4. **Critical: Inconsistent MediaRecorder Setup** (VoiceButton.jsx)
**Location:** `frontend/src/components/VoiceButton.jsx` lines 308-309 (before fix)
**Issue:** Conditional MediaRecorder creation based on mime type availability:
```javascript
// OLD - problematic:
const rec = mime ? new MediaRecorder(stream, { mimeType: mime }) : new MediaRecorder(stream);
```
**Impact:** When no supported mime type was found, MediaRecorder was created without mimeType specification, causing unpredictable codec selection and potential audio capture failures.
**Fix:** Extracted mime selection into `recOptions` object:
```javascript
const recOptions = mime ? { mimeType: mime } : {};
const rec = new MediaRecorder(stream, recOptions);
```

---

### 5. **Critical: Ambiguous Blob MIME Type** (VoiceButton.jsx)
**Location:** `frontend/src/components/VoiceButton.jsx` line 321 (before fix)
**Issue:** Blob MIME type fallback chain was unclear:
```javascript
// OLD:
const blob = new Blob(chunksRef.current, { type: rec.mimeType || mime || "audio/webm" });
```
**Impact:** `rec.mimeType` may be undefined, relying on fallback `mime` variable which could be empty string.
**Fix:** Explicitly extract and validate MIME type:
```javascript
const mimeType = rec.mimeType || mime || "audio/webm";
const blob = new Blob(chunksRef.current, { type: mimeType });
```

---

### 6. **High: Silent Error Suppression** (VoiceButton.jsx)
**Location:** `frontend/src/components/VoiceButton.jsx` line 341 (before fix)
**Issue:** Error catching with underscore (`catch (_)`) was silently ignoring ASR failures:
```javascript
// OLD:
} catch (_) {
  setErrorMsg(t(langRef.current, "asrError"));
}
```
**Impact:** Real errors (network, server errors, permission issues) were masked, making debugging impossible and preventing users from seeing detailed error info in console.
**Fix:** Added proper error logging:
```javascript
} catch (err) {
  console.error("ASR transcription failed:", err);
  setErrorMsg(t(langRef.current, "asrError"));
}
```

---

## Audio Input Flow After Fixes

1. **Frontend** calls `/api/asr/status` to check if server Whisper is available
2. **User clicks** voice button → `startServerCapture()` executes
3. **MediaRecorder** is created with proper MIME type (webm/opus, webm, mp4, or ogg)
4. **Audio** is recorded with silence detection (2s of silence auto-stops recording)
5. **Blob** is created with correct MIME type
6. **FormData** includes audio blob with proper filename (`blobFilename()`)
7. **POST /api/asr** with audio → backend decodes with ffmpeg/PyAV
8. **Response** includes transcript, confidence, and engine info
9. **Error handling** now shows meaningful messages to user

---

## Files Modified

- `frontend/src/api.js` - Fixed function hoisting and added asrStatus()
- `frontend/src/components/VoiceButton.jsx` - Fixed variable references, MediaRecorder setup, error handling, and logging

---

## Testing Recommendations

1. Test microphone permission denial → should show error message
2. Test with audio/webm support available → should use opus
3. Test with no supported MIME types → should fallback to webm
4. Test ASR endpoint offline → should show transcription error
5. Test silence detection → should auto-stop after 2s silence
6. Check browser console → should show "ASR transcription failed:" on errors
7. Test engine switching → should allow switching between Web Speech and Whisper
