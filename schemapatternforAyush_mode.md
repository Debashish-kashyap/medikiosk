schema pattern from `clinical_ontology.json` (node → field/section/type/prompt{en,hi,as}/options{value,label,icon,aliases,next}). Here's the AYUSH module built to match it exactly.

### **Design decision: how AYUSH mode plugs into the existing graph**

The ontology is a **deterministic dialogue graph** traversed by `next` pointers, with the LLM only mapping free speech onto option values. AYUSH mode shouldn't fork the *entry* node — it should be a **session-level flag** (`ayush_mode: true/false`, set by the frontend toggle) that decides whether the tail of the flow routes through 5 new AYUSH nodes before hitting `past_history`, or skips straight there as today.

So: every existing complaint branch already points to `"next": "past_history"`. We insert one new entry node, `ayush_check`, between the complaint branches and `past_history`, and make it a no-op passthrough for General mode:

chief\_complaint → \[chest\_pain / fever / cough / ...\] → ayush\_check → past\_history

`ayush_check` isn't shown to the patient — it's resolved server-side by the router: if `session.ayush_mode` is `true`, jump to `ayush_prakriti`; if `false`, jump straight to `past_history`. (I've marked it below as a `router_node`, not a `single_select`, since it needs a one-line change in `dialogue.py`, not the frontend.)

### **The 5 AYUSH nodes (ontology JSON)**

json  
"ayush\_prakriti": {  
  "id": "ayush\_prakriti",  
  "field": "ayush\_prakriti\_cue",  
  "section": "ayush",  
  "type": "single\_select",  
  "allow\_voice": true,  
  "prompt": {  
    "en": "Which best describes your body build and appetite?",  
    "hi": "आपके शरीर की बनावट और भूख को कौन सा विकल्प सबसे अच्छे से बताता है?",  
    "as": "আপোনাৰ শৰীৰৰ গঠন আৰু ভোক কোনটোৱে সবচেয়ে ভালদৰে বৰ্ণনা কৰে?"  
  },  
  "help": {  
    "en": "This is a preliminary cue only — the vaidya will confirm your Prakriti in person.",  
    "hi": "यह केवल एक प्रारंभिक संकेत है — वैद्य आपसे मिलकर आपकी प्रकृति की पुष्टि करेंगे।",  
    "as": "এইটো কেৱল প্ৰাথমিক ইংগিত — বৈদ্যই সাক্ষাতে আপোনাৰ প্ৰকৃতি নিশ্চিত কৰিব।"  
  },  
  "options": \[  
    {  
      "value": "vata\_leaning",  
      "label": { "en": "Thin build, feels cold easily, variable appetite", "hi": "पतला शरीर, जल्दी ठंड लगती है, भूख अनियमित", "as": "পাতল গঠন, সহজে জাৰ লাগে, ভোক অনিয়মীয়া" },  
      "icon": "wind",  
      "aliases": \["thin", "cold", "variable appetite", "patla", "thanda lagta hai", "patol", "jaar lage"\]  
    },  
    {  
      "value": "pitta\_leaning",  
      "label": { "en": "Medium build, strong appetite, tends to feel warm", "hi": "मध्यम शरीर, तेज़ भूख, गर्मी ज़्यादा लगती है", "as": "মধ্যম গঠন, শক্তিশালী ভোক, গৰম বেছি লাগে" },  
      "icon": "flame",  
      "aliases": \["medium build", "strong appetite", "warm", "garam lagta hai", "tez bhookh", "gorom lage"\]  
    },  
    {  
      "value": "kapha\_leaning",  
      "label": { "en": "Solid build, steady appetite, gains weight easily", "hi": "मज़बूत शरीर, स्थिर भूख, वज़न जल्दी बढ़ता है", "as": "টান গঠন, স্থিৰ ভোক, ওজন সহজে বৃদ্ধি পায়" },  
      "icon": "shield",  
      "aliases": \["solid build", "steady appetite", "weight gain", "mota", "wazan badhta hai", "bhori diye"\]  
    },  
    {  
      "value": "not\_sure",  
      "label": { "en": "Not sure", "hi": "पता नहीं", "as": "নিশ্চিত নহয়" },  
      "icon": "help-circle",  
      "aliases": \["not sure", "pata nahi", "malum nahi", "najanu"\]  
    }  
  \],  
  "next": "ayush\_agni"  
},

"ayush\_agni": {  
  "id": "ayush\_agni",  
  "field": "ayush\_ahara\_shakti",  
  "section": "ayush",  
  "type": "single\_select",  
  "allow\_voice": true,  
  "prompt": {  
    "en": "How would you describe your digestion most days?",  
    "hi": "ज़्यादातर दिनों में आपका पाचन कैसा रहता है?",  
    "as": "বেছিভাগ দিনত আপোনাৰ পাচন কেনেকুৱা থাকে?"  
  },  
  "options": \[  
    {  
      "value": "irregular",  
      "label": { "en": "Irregular — sometimes bloated, sometimes fine", "hi": "अनियमित — कभी पेट फूला, कभी ठीक", "as": "অনিয়মীয়া — কেতিয়াবা পেট ফুলে, কেতিয়াবা ঠিক" },  
      "icon": "activity",  
      "aliases": \["irregular digestion", "bloating", "gas weekly", "pet phoolta hai", "kobhi thik kobhi kharab"\]  
    },  
    {  
      "value": "strong",  
      "label": { "en": "Strong / sharp — hungry often, digests fast", "hi": "तेज़ — बार-बार भूख लगती है, जल्दी पचता है", "as": "শক্তিশালী — সঘনাই ভোক লাগে, সোনকালে হজম হয়" },  
      "icon": "zap",  
      "aliases": \["strong digestion", "hungry often", "fast digestion", "tez bhookh", "jaldi bhookh lagti hai"\]  
    },  
    {  
      "value": "slow\_heavy",  
      "label": { "en": "Slow / heavy — feels full a long time, sluggish", "hi": "धीमा / भारी — देर तक पेट भरा लगता है", "as": "লাহে / গধুৰ — বহু সময় পেট ভৰি থকা যেন লাগে" },  
      "icon": "battery-low",  
      "aliases": \["slow digestion", "heavy stomach", "sluggish", "pet bhaari lagta hai"\]  
    },  
    {  
      "value": "currently\_disturbed",  
      "label": { "en": "Currently disturbed (nausea, acidity, loose motion)", "hi": "अभी गड़बड़ है (जी मिचलाना, एसिडिटी, दस्त)", "as": "বৰ্তমান বিঘ্নিত (বমি ভাব, এচিডিটি, পেট চলা)" },  
      "icon": "alert-triangle",  
      "aliases": \["nausea", "acidity", "loose motion", "vomiting", "jee michlana", "dast", "pet chola"\],  
      "flag": "vikriti\_active"  
    }  
  \],  
  "next": "ayush\_sleep\_bowel"  
},

"ayush\_sleep\_bowel": {  
  "id": "ayush\_sleep\_bowel",  
  "field": "ayush\_vikriti\_current",  
  "section": "ayush",  
  "type": "multi\_select",  
  "allow\_voice": true,  
  "prompt": {  
    "en": "How have your sleep and bowel movements been recently?",  
    "hi": "हाल ही में आपकी नींद और मल त्याग कैसे रहे हैं?",  
    "as": "শেহতীয়াকৈ আপোনাৰ টোপনি আৰু পেটৰ কাম কেনেকুৱা হৈছে?"  
  },  
  "options": \[  
    {  
      "value": "sleep\_sound",  
      "label": { "en": "Sleep: sound", "hi": "नींद: अच्छी", "as": "টোপনি: ভাল" },  
      "group": "sleep",  
      "aliases": \["good sleep", "sound sleep", "achi neend"\]  
    },  
    {  
      "value": "sleep\_disturbed",  
      "label": { "en": "Sleep: disturbed", "hi": "नींद: बाधित", "as": "টোপনি: বিঘ্নিত" },  
      "group": "sleep",  
      "aliases": \["disturbed sleep", "neend nahi aati", "wake up at night"\]  
    },  
    {  
      "value": "sleep\_very\_little",  
      "label": { "en": "Sleep: very little", "hi": "नींद: बहुत कम", "as": "টোপনি: বহুত কম" },  
      "group": "sleep",  
      "aliases": \["very little sleep", "kam neend", "insomnia"\]  
    },  
    {  
      "value": "bowel\_regular",  
      "label": { "en": "Bowel: regular", "hi": "मल त्याग: नियमित", "as": "পেটৰ কাম: নিয়মীয়া" },  
      "group": "bowel",  
      "aliases": \["regular bowel", "normal motion"\]  
    },  
    {  
      "value": "bowel\_irregular",  
      "label": { "en": "Bowel: irregular", "hi": "मल त्याग: अनियमित", "as": "পেটৰ কাম: অনিয়মীয়া" },  
      "group": "bowel",  
      "aliases": \["irregular bowel"\]  
    },  
    {  
      "value": "bowel\_constipated",  
      "label": { "en": "Bowel: constipated", "hi": "मल त्याग: कब्ज़", "as": "পেটৰ কাম: কোষ্ঠকাঠিন্য" },  
      "group": "bowel",  
      "aliases": \["constipation", "kabj", "kabz"\]  
    },  
    {  
      "value": "bowel\_loose",  
      "label": { "en": "Bowel: loose", "hi": "मल त्याग: पतला/ढीला", "as": "পেটৰ কাম: পাতল" },  
      "group": "bowel",  
      "aliases": \["loose motion", "dast", "diarrhea"\]  
    }  
  \],  
  "next": "ayush\_satmya"  
},

"ayush\_satmya": {  
  "id": "ayush\_satmya",  
  "field": "ayush\_satmya",  
  "section": "ayush",  
  "type": "free\_text",  
  "allow\_voice": true,  
  "prompt": {  
    "en": "Do certain foods, weather, or seasons clearly disagree with you?",  
    "hi": "क्या कोई खाना, मौसम, या ऋतु आपको साफ़ तौर पर सूट नहीं करती?",  
    "as": "কিছুমান খাদ্য, বতৰ, বা ঋতুৱে আপোনাক স্পষ্টকৈ অসুবিধা কৰেনে?"  
  },  
  "help": {  
    "en": "Say or type freely — e.g. 'cold weather', 'dairy', 'spicy food', or 'none that I've noticed'.",  
    "hi": "स्वतंत्र रूप से बोलें या टाइप करें — जैसे 'ठंड का मौसम', 'डेयरी', 'मसालेदार खाना', या 'कुछ खास नहीं'।",  
    "as": "মুক্তভাৱে কওক বা টাইপ কৰক — যেনে 'জাৰৰ বতৰ', 'গাখীৰজাত সামগ্ৰী', 'জিলাপীয়া খাদ্য', বা 'একো লক্ষ্য কৰা নাই'।"  
  },  
  "quick\_options": \[  
    { "value": "cold\_weather", "label": { "en": "Cold weather", "hi": "ठंड का मौसम", "as": "জাৰৰ বতৰ" } },  
    { "value": "hot\_weather", "label": { "en": "Hot weather", "hi": "गर्मी", "as": "গৰম বতৰ" } },  
    { "value": "dairy", "label": { "en": "Dairy", "hi": "डेयरी", "as": "গাখীৰজাত" } },  
    { "value": "spicy\_food", "label": { "en": "Spicy food", "hi": "मसालेदार खाना", "as": "জিলাপীয়া খাদ্য" } },  
    { "value": "none\_noticed", "label": { "en": "None noticed", "hi": "कुछ खास नहीं", "as": "একো লক্ষ্য কৰা নাই" } }  
  \],  
  "next": "ayush\_satva"  
},

"ayush\_satva": {  
  "id": "ayush\_satva",  
  "field": "ayush\_satva",  
  "section": "ayush",  
  "type": "single\_select",  
  "allow\_voice": true,  
  "optional": true,  
  "prompt": {  
    "en": "How would you say you're handling stress or worry lately?",  
    "hi": "हाल ही में आप तनाव या चिंता को कैसे संभाल रहे हैं?",  
    "as": "শেহতীয়াকৈ আপুনি চিন্তা বা মানসিক চাপ কেনেকৈ সামাল দিছে?"  
  },  
  "help": {  
    "en": "This question is optional and confidential — you may skip it.",  
    "hi": "यह सवाल वैकल्पिक और गोपनीय है — आप इसे छोड़ सकते हैं।",  
    "as": "এই প্ৰশ্নটো বৈকল্পিক আৰু গোপনীয় — আপুনি এইটো এৰি যাব পাৰে।"  
  },  
  "options": \[  
    {  
      "value": "calm\_steady",  
      "label": { "en": "Calm and steady", "hi": "शांत और स्थिर", "as": "শান্ত আৰু স্থিৰ" },  
      "icon": "smile",  
      "aliases": \["calm", "fine", "steady", "theek hoon"\]  
    },  
    {  
      "value": "anxious\_restless",  
      "label": { "en": "Anxious / restless most days", "hi": "ज़्यादातर दिन बेचैन / चिंतित", "as": "বেছিভাগ দিনতে চিন্তিত / অস্থিৰ" },  
      "icon": "alert-circle",  
      "aliases": \["anxious", "restless", "worried", "chinta", "bechaini"\]  
    },  
    {  
      "value": "low\_fatigued",  
      "label": { "en": "Low mood / fatigued", "hi": "उदास / थका हुआ महसूस होता है", "as": "মন বেয়া / ভাগৰুৱা লাগে" },  
      "icon": "battery-low",  
      "aliases": \["low mood", "fatigued", "tired", "udaas", "thaka hua"\]  
    },  
    {  
      "value": "prefer\_not\_to\_answer",  
      "label": { "en": "Prefer not to answer", "hi": "जवाब नहीं देना चाहता/चाहती", "as": "উত্তৰ দিব নিবিচাৰো" },  
      "icon": "lock",  
      "aliases": \["skip", "prefer not to say", "nahi bataana chahta"\]  
    }  
  \],  
  "next": "past\_history"  
}

### **Wiring notes for `dialogue.py` / `ontology_loader.py`**

1. **Session flag, not a node the patient sees**: add `ayush_mode: bool = False` to the session model (wherever `session.py` tracks state — likely alongside `language`). The frontend toggle (General/AYUSH switch you're building) sets this once at intake start, same moment language is picked.  
2. **One conditional in the router**, at the point where a complaint branch currently resolves `next: "past_history"`:

python  
def resolve\_next(node, session):  
    nxt \= node.get("next")  
    if nxt \== "past\_history" and session.ayush\_mode and not session.get("ayush\_done"):  
        return "ayush\_prakriti"  
    return nxt

And at the end of `ayush_satva`, set `session["ayush_done"] = True` before falling into `past_history` — so AYUSH mode adds exactly one pass through the 5 nodes, not a loop.

3. **`ayush_sleep_bowel` uses `type: "multi_select"`** and `ayush_satmya` uses `type: "free_text"` with `quick_options` — if your frontend's node renderer only currently handles `single_select`, these two will need a small UI branch (checkbox group \+ free-text-with-chips). Everything else matches your existing `single_select` pattern exactly, so those three nodes (`ayush_prakriti`, `ayush_agni`, `ayush_satva`) should render with **zero frontend changes**.  
4. **Translations**: I've done best-effort Hindi/Assamese matching your existing tone, but given the Assamese corruption bug we found earlier in `asr_engine.py`, I'd strongly recommend having a native speaker proofread the `"as"` strings before this goes in the ontology file — and double-check the file saves as clean UTF-8 this time.

Want me to also draft the `ayush_intro` micro-screen (the one-line explanation shown right when AYUSH mode is toggled on, before `ayush_prakriti` starts) so the patient understands why they're being asked these extra questions?

yes

Here's the `ayush_intro` node — shown once, right after the toggle is switched to AYUSH mode and before `ayush_prakriti` begins. It needs to set expectations (why extra questions, how long, that it's not replacing the doctor) so patients don't feel surprised or over-probed.

json  
"ayush\_intro": {  
  "id": "ayush\_intro",  
  "field": null,  
  "section": "ayush",  
  "type": "info\_screen",  
  "allow\_voice": false,  
  "prompt": {  
    "en": "You've chosen an AYUSH consultation. A few extra questions help your vaidya understand your constitution and current balance — this takes about 60–90 seconds.",  
    "hi": "आपने आयुष परामर्श चुना है। कुछ अतिरिक्त सवाल आपके वैद्य को आपकी प्रकृति और वर्तमान संतुलन समझने में मदद करेंगे — इसमें लगभग 60–90 सेकंड लगेंगे।",  
    "as": "আপুনি আয়ুষ পৰামৰ্শ বাছি লৈছে। কিছুমান অতিৰিক্ত প্ৰশ্নই আপোনাৰ বৈদ্যক আপোনাৰ প্ৰকৃতি আৰু বৰ্তমানৰ সন্তুলন বুজাত সহায় কৰিব — ইয়াত প্ৰায় ৬০–৯০ ছেকেণ্ড লাগিব।"  
  },  
  "help": {  
    "en": "These questions don't replace your vaidya's examination — they simply save time so your consultation can focus on you.",  
    "hi": "ये सवाल आपके वैद्य की जांच का विकल्प नहीं हैं — ये सिर्फ समय बचाते हैं ताकि परामर्श आप पर केंद्रित रह सके।",  
    "as": "এই প্ৰশ্নবোৰে আপোনাৰ বৈদ্যৰ পৰীক্ষাৰ পৰিবৰ্তে নহয় — ই কেৱল সময় ৰাখি থয় যাতে পৰামৰ্শটো আপোনাতে কেন্দ্ৰীভূত হৈ থাকে।"  
  },  
  "cta": {  
    "en": "Start",  
    "hi": "शुरू करें",  
    "as": "আৰম্ভ কৰক"  
  },  
  "skip\_option": {  
    "en": "Skip this section",  
    "hi": "यह भाग छोड़ें",  
    "as": "এই খণ্ড এৰি যাওক"  
  },  
  "next": "ayush\_prakriti"  
}

### **Why it's shaped this way**

* **`type: "info_screen"`** — a new type, distinct from `single_select`/`multi_select`/`free_text`. It's not a question; it's a one-tap "Start" acknowledgment. Needs one small frontend addition: a simple card with prompt text, a Start button, and a Skip link — no option-rendering logic needed, so it's cheap to add.  
* **`allow_voice: false`** — nothing to transcribe here; keeps it simple.  
* **Explicit "doesn't replace the vaidya" line** — directly defensible against a judge's "why is a kiosk asking Ayurvedic diagnostic questions" pushback, and it's honest about scope.  
* **`skip_option`** — important for patient autonomy. AYUSH mode is opt-in already (via your General/AYUSH toggle), but a patient may still want to skip the extra module once they see it's 5 more questions. If skipped, session should route straight to `past_history`, same as General mode — set `session["ayush_done"] = True` on skip too, so it doesn't re-trigger.  
* **Time estimate ("60–90 seconds")** — ties directly back to your problem brief's core pitch (pre-consult layer that's fast, not another bottleneck) — worth keeping in the demo narrative.

### **Toggle placement (for your General/AYUSH switch)**

One flow suggestion: put the toggle **before** `chief_complaint`, at the same screen as language selection — not after, since AYUSH framing should color how the whole intake is greeted, not just tacked onto the end. If AYUSH is selected there, `ayush_intro` fires automatically right after the chief-complaint branch resolves, using the router logic from before

