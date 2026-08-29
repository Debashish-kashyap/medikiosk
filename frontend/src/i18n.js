// UI-chrome strings only. Clinical question text is localized by the backend
// (from clinical_ontology.json), so it is NOT duplicated here.

export const UI = {
  en: {
    appTitle: "MediKiosk",
    tagline: "Tell us about your health before you see the doctor",
    chooseLanguage: "Choose your language",
    consentTitle: "Your privacy",
    consentBody:
      "We will note down what you tell us and share it only with your doctor for this visit. Your information is kept secure and cleared after your visit. Do you agree to continue?",
    consentAgree: "I agree — continue",
    listening: "Listening… please speak",
    speak: "Tap and speak",
    tapPrompt: "…or tap an option",
    orType: "or choose below",
    confirmHeading: "Did you mean:",
    confirmYes: "Yes, that's right",
    confirmNo: "No — let me choose",
    done: "Done",
    next: "Next",
    back: "Back",
    summaryTitle: "History summary (for the doctor)",
    forPhysician: "Physician view — review, edit, confirm",
    uploadDoc: "Add a report / prescription",
    generateFhir: "Finish & generate record",
    restart: "New patient",
    redFlag: "Priority alert",
    physicianNote: "History of present illness (editable)",
    submitted: "Record generated",
    abdmNote: "FHIR bundle ready. ABDM push is mocked for this demo.",
    voiceUnsupported: "Voice input isn't available in this browser — please tap an option.",
    micPermissionDenied: "Microphone permission was denied — please allow access and try again.",
    micNotFound: "No microphone found — please connect one or tap an option.",
    recordingTimeout: "Recording stopped — maximum time reached.",
    asrProcessing: "Processing your speech…",
    asrError: "Could not understand — please try again or tap an option.",
    speechNetworkError:
      "Browser speech needs internet (Chrome/Edge). Allow the microphone, or tap an option.",
  },
  hi: {
    appTitle: "मेडीकियोस्क",
    tagline: "डॉक्टर से मिलने से पहले अपनी सेहत के बारे में बताएं",
    chooseLanguage: "अपनी भाषा चुनें",
    consentTitle: "आपकी निजता",
    consentBody:
      "आप जो बताएंगे उसे हम नोट करेंगे और केवल इस मुलाकात के लिए आपके डॉक्टर से साझा करेंगे। आपकी जानकारी सुरक्षित रहती है और मुलाकात के बाद हटा दी जाती है। क्या आप आगे बढ़ना चाहते हैं?",
    consentAgree: "मैं सहमत हूँ — आगे बढ़ें",
    listening: "सुन रहे हैं… कृपया बोलें",
    speak: "दबाएँ और बोलें",
    tapPrompt: "…या विकल्प चुनें",
    orType: "या नीचे चुनें",
    confirmHeading: "क्या आपका मतलब था:",
    confirmYes: "हाँ, सही है",
    confirmNo: "नहीं — मैं चुनता हूँ",
    done: "पूरा",
    next: "आगे",
    back: "पीछे",
    summaryTitle: "इतिहास सारांश (डॉक्टर के लिए)",
    forPhysician: "डॉक्टर व्यू — समीक्षा, संपादन, पुष्टि",
    uploadDoc: "रिपोर्ट / पर्ची जोड़ें",
    generateFhir: "समाप्त करें और रिकॉर्ड बनाएं",
    restart: "नया मरीज़",
    redFlag: "प्राथमिकता चेतावनी",
    physicianNote: "वर्तमान बीमारी का इतिहास (संपादन योग्य)",
    submitted: "रिकॉर्ड तैयार",
    abdmNote: "FHIR बंडल तैयार। इस डेमो में ABDM पुश मॉक है।",
    voiceUnsupported: "इस ब्राउज़र में वॉइस उपलब्ध नहीं — कृपया विकल्प चुनें।",
    micPermissionDenied: "माइक्रोफ़ोन अनुमति नहीं मिली — कृपया अनुमति दें और पुनः प्रयास करें।",
    micNotFound: "माइक्रोफ़ोन नहीं मिला — कृपया एक कनेक्ट करें या विकल्प चुनें।",
    recordingTimeout: "रिकॉर्डिंग रुक गई — अधिकतम समय पूरा।",
    asrProcessing: "आपकी बात समझ रहे हैं…",
    asrError: "समझ नहीं आया — कृपया फिर बोलें या विकल्प चुनें।",
    speechNetworkError:
      "ब्राउज़र वॉइस के लिए इंटरनेट चाहिए (Chrome/Edge)। माइक अनुमति दें, या विकल्प चुनें।",
  },
};

export function t(lang, key) {
  const table = UI[lang] || UI.en;
  return table[key] ?? UI.en[key] ?? key;
}

export const LANGUAGES = [
  { code: "en", label: "English" },
  { code: "hi", label: "हिन्दी" },
];

// BCP-47 tags for the browser Web Speech API.
export const SPEECH_LANG = { en: "en-IN", hi: "hi-IN" };
