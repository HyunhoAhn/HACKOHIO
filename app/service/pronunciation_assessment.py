import azure.cognitiveservices.speech as speechsdk
from app.utils.env_loader import get_settings

def pronunciation_assessment(wav_file: str, reference_text: str, language: str = "en-US"):
    settings = get_settings()

    speech_key = settings.SPEECH_KEY
    speech_region = settings.SPEECH_REGION

    if not speech_key or not speech_region:
        print("⚠️  SPEECH_KEY and SPEECH_REGION did not set (check .env).")
        return

    speech_config = speechsdk.SpeechConfig(subscription=speech_key, region=speech_region)
    audio_config = speechsdk.AudioConfig(filename=wav_file)

    pronunciation_config = speechsdk.PronunciationAssessmentConfig(
        reference_text=reference_text,
        grading_system=speechsdk.PronunciationAssessmentGradingSystem.HundredMark,
        granularity=speechsdk.PronunciationAssessmentGranularity.Phoneme,
        enable_miscue=False
    )
    pronunciation_config.enable_prosody_assessment()

    recognizer = speechsdk.SpeechRecognizer(
        speech_config=speech_config,
        language=language,
        audio_config=audio_config
    )

    pronunciation_config.apply_to(recognizer)

    print("🎤 Evaluate pronunciation...")
    result = recognizer.recognize_once_async().get()

    if result.reason == speechsdk.ResultReason.RecognizedSpeech:
        pa_result = speechsdk.PronunciationAssessmentResult(result)
        print(f"\n📜 Transcribed result: {result.text}")
        print(f"Accuracy: {pa_result.accuracy_score}")
        print(f"Fluency: {pa_result.fluency_score}")
        print(f"Completeness: {pa_result.completeness_score}")
        print(f"Overall: {pa_result.pronunciation_score}\n")

    elif result.reason == speechsdk.ResultReason.NoMatch:
        print("❌ Cannot recognize the voice.")
    elif result.reason == speechsdk.ResultReason.Canceled:
        print("🚫 Evaluation canceled:")
        print(result.cancellation_details.reason)
        if result.cancellation_details.reason == speechsdk.CancellationReason.Error:
            print(f"Error: {result.cancellation_details.error_details}")

    return result.json