# Every Bangla string here is a DRAFT — needs native speaker review before recording.
"""UI strings and consent text. Strings marked NEW need C's wording or approval in step 06."""
CONSENT_VERSION = "2026-10-10-draft1"   # bump whenever CONSENT_BN changes

CONSENT_BN = (
    "কম বিষ একটা কম্পিউটার প্রোগ্রাম, সরকারি কর্মকর্তা নয়। আপনার ছবি শুধু পরামর্শ দেওয়ার জন্য দেখা হয়, আমরা ছবি রাখি না। "
    "ভয়েস নোট দিলে সেটা দেশের বাইরে Google-এর সার্ভারে প্রক্রিয়া হয়, আর Google তার সেবা উন্নত করতে এটা ব্যবহার করতে পারে; "
    "আমরা রেকর্ডিং রাখি না। আমরা শুধু ফলাফল রাখি, কোন রোগ মনে হয়েছে আর কী পরামর্শ দেওয়া হয়েছে, নাম বা ফোন নম্বর ছাড়া। "
    "আপনার বয়স আঠারোর কম হলে মা-বাবার অনুমতি লাগবে। রাজি থাকলে টিক দিন।"
)
CONSENT_GLOSS_EN = (
    "Kom Bish is a computer program, not a government officer. Your photo is only looked at to give advice; we do not keep it. "
    "If you add a voice note, it is processed on Google's servers outside the country, and Google may use it to improve its "
    "services; we do not keep the recording. We keep only the result, what disease it looked like and what advice was given, "
    "without name or phone number. Under eighteen needs a parent's permission. Tick if you agree."
)
CONSENT_CHECKBOX_BN = "রাজি থাকলে টিক দিন।"
VOICE_PRIVACY_NOTE_BN = "ভয়েস নোট Google-এর সার্ভারে প্রক্রিয়া হয়"
LABEL_PHOTO_BN = "ধানের পাতার ছবি"
LABEL_VOICE_BN = "ভয়েস নোট (ঐচ্ছিক)"
BUTTON_ADVISE_BN = "পরামর্শ নিন"
LABEL_LISTEN_BN = "শুনুন"
TAB_ADVICE_BN = "পরামর্শ"
TAB_DASHBOARD_BN = "ড্যাশবোর্ড"
SPRAY_INTENT_Q_BN = "আপনি কি স্প্রে করার কথা ভাবছিলেন?"
YES_BN, NO_BN = "হ্যাঁ", "না"
NOT_SURE_BN = "নিশ্চিত নই"                           # NEW ("not sure"), DRAFT written 11 Oct 2026 for review.
# The lesion-shape question asked before any blast (spray) answer is the R0_CONFIRM_BLAST headline in
# data/rules.csv. Yes -> the blast answer. No or not sure -> referral.
CONFIRM_TEMPLATE_BN = "ছবি দেখে মনে হচ্ছে আপনার ধানে {disease}।"
DISEASE_NAME_BN = {"bacterial_leaf_blight": "পাতাপোড়া রোগ", "blast": "ব্লাস্ট রোগ"}
VOICE_ECHO_BN = "আপনি বলছেন: “{transcript}”"     # from the draft "আপনি বলছেন, ..."
SOURCE_LABEL_BN = "সূত্র"                           # NEW
LABEL_SAFETY_BN = "স্প্রের নিরাপত্তা"                  # NEW
FEEDBACK_BN = "ভুল মনে হচ্ছে"                        # NEW ("this looks wrong")
FEEDBACK_THANKS_BN = "ধন্যবাদ"                       # NEW
# Shown next to the audio players while the clips are generated with text-to-speech, not recorded by a person.
AUDIO_SYNTHETIC_NOTE_BN = "কম্পিউটারে তৈরি কণ্ঠ"        # NEW ("computer-generated voice"), DRAFT written 11 Oct 2026

# ---- English translations, shown only when the "Show English" toggle is on (for reviewers and judges).
# The farmer-facing app and the audio are Bangla. Keep each line in step with its Bangla original.
SHOW_ENGLISH_LABEL = "Show English (for reviewers)"
ENGLISH_NOTE = "*English translation for reviewers. The app and the audio are in Bangla.*"
CONSENT_CHECKBOX_EN = "Tick if you agree."
LABEL_PHOTO_EN = "Photo of a rice leaf"
SPRAY_INTENT_Q_EN = "Were you thinking of spraying?"
CONFIRM_TEMPLATE_EN = "From the photo, it looks like your rice has {disease}."
DISEASE_NAME_EN = {"bacterial_leaf_blight": "bacterial leaf blight", "blast": "blast"}
SOURCE_LABEL_EN = "Source"


def both(bn: str, en: str, show_english: bool) -> str:
    """A label in Bangla, with its English translation after it when the toggle is on."""
    return f"{bn} / {en}" if show_english else bn
