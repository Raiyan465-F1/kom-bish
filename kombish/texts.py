# Every Bangla string here was reviewed by one native speaker on 2026-10-11 (the reviewer is named in
# data/clips.csv). Do not reword a reviewed string without the team's approval; a new string is a DRAFT.
"""UI strings and consent text, with the English translations shown by the "Show English" toggle."""
CONSENT_VERSION = "2026-10-11-v1"   # bump whenever CONSENT_BN changes

CONSENT_BN = (
    "কম বিষ, একটি কম্পিউটার প্রোগ্রাম; কোনো সরকারি কর্মকর্তা নয়। আমরা আপনার ছবি বা ভয়েস রেকর্ডিং রাখি না। "
    "শুধু কোন রোগ মনে হয়েছে আর কী পরামর্শ দেওয়া হয়েছে, তা রাখি, নাম বা ফোন নম্বর ছাড়া। "
    "ভয়েস নোট দিলে তা দেশের বাইরে Google-এর সার্ভারে প্রক্রিয়া করা হয়, আর Google তার সেবা উন্নত করতে এটি ব্যবহার করতে পারে। "
    "বয়স আঠারোর কম হলে মা-বাবার অনুমতি নিন। রাজি থাকলে টিক দিন।"
)
CONSENT_GLOSS_EN = (
    "Kom Bish is a computer program, not a government officer. We do not keep your photo or your voice recording. "
    "We keep only what disease it looked like and what advice was given, without name or phone number. If you add a "
    "voice note, it is processed on Google's servers outside the country, and Google may use it to improve its "
    "services. If you are under eighteen, get your parents' permission. Tick if you agree."
)
CONSENT_CHECKBOX_BN = "রাজি থাকলে টিক দিন।"
VOICE_PRIVACY_NOTE_BN = "ভয়েস নোট Google-এর সার্ভারে প্রক্রিয়া করা হয়"
# Shown above the photo box. The model works on a close-up of one leaf, not on a wide shot of plants.
PHOTO_INSTRUCTION_BN = "একটি পাতার কাছ থেকে ছবি তুলুন, পাতাটা যেন পুরো পর্দা জুড়ে থাকে। দিনের আলোতে তুলুন।"
LABEL_PHOTO_BN = "ধানের পাতার ছবি"
LABEL_VOICE_BN = "ভয়েস নোট (ঐচ্ছিক)"
BUTTON_ADVISE_BN = "পরামর্শ নিন"
LABEL_LISTEN_BN = "শুনুন"
TAB_ADVICE_BN = "পরামর্শ"
TAB_DASHBOARD_BN = "ড্যাশবোর্ড"
SPRAY_INTENT_Q_BN = "আপনি কি স্প্রে করার কথা ভাবছেন?"
YES_BN, NO_BN = "হ্যাঁ", "না"
NOT_SURE_BN = "নিশ্চিত নই"
# The lesion-shape question asked before any blast (spray) answer is the R0_CONFIRM_BLAST headline in
# data/rules.csv. Yes -> the blast answer. No or not sure -> referral.
CONFIRM_TEMPLATE_BN = "ছবি দেখে মনে হচ্ছে আপনার ধানে {disease} হয়েছে।"
DISEASE_NAME_BN = {"bacterial_leaf_blight": "পাতা পোড়া রোগ", "blast": "ব্লাস্ট রোগ"}
VOICE_ECHO_BN = 'আপনি বলেছেন: "{transcript}"'
SOURCE_LABEL_BN = "সূত্র"
LABEL_SAFETY_BN = "স্প্রের নিরাপত্তা"
FEEDBACK_BN = "ভুল মনে হচ্ছে"
FEEDBACK_THANKS_BN = "ধন্যবাদ"
# Shown next to the audio players while the clips are generated with text-to-speech, not recorded by a person.
AUDIO_SYNTHETIC_NOTE_BN = "কম্পিউটারে তৈরি কণ্ঠ"

# ---- English translations, shown only when the "Show English" toggle is on (for reviewers and judges).
# The farmer-facing app and the audio are Bangla. Keep each line in step with its Bangla original.
SHOW_ENGLISH_LABEL = "Show English (for reviewers)"
ENGLISH_NOTE = "*English translation for reviewers. The app and the audio are in Bangla.*"
CONSENT_CHECKBOX_EN = "Tick if you agree."
PHOTO_INSTRUCTION_EN = "Take the photo close to one leaf, so that the leaf fills the whole screen. Take it in daylight."
LABEL_PHOTO_EN = "Photo of a rice leaf"
SPRAY_INTENT_Q_EN = "Are you thinking of spraying?"
CONFIRM_TEMPLATE_EN = "From the photo, it looks like your rice has {disease}."
DISEASE_NAME_EN = {"bacterial_leaf_blight": "bacterial leaf blight", "blast": "blast"}
SOURCE_LABEL_EN = "Source"


def both(bn: str, en: str, show_english: bool) -> str:
    """A label in Bangla, with its English translation after it when the toggle is on."""
    return f"{bn} / {en}" if show_english else bn
