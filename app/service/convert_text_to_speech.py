import azure.cognitiveservices.speech as speechsdk
from app.utils.env_loader import get_settings

def convert_text_to_speech(prompt: str, output_file: str = "./out.wav", voice: str = "en-US-AndrewMultilingualNeural"):
    settings = get_settings()

    speech_key = settings.SPEECH_KEY
    speech_region = settings.SPEECH_REGION

    if not speech_key or not speech_region:
        print("⚠️  SPEECH_KEY and SPEECH_REGION did not set (check .env).")
        return

    speech_config = speechsdk.SpeechConfig(subscription=speech_key, region=speech_region)

    # 원하는 음성 지정 (예시)
    speech_config.speech_synthesis_voice_name = voice

    audio_config = speechsdk.audio.AudioOutputConfig(filename="./"+output_file)
    synth = speechsdk.SpeechSynthesizer(speech_config=speech_config,
                                        audio_config=audio_config)

    result = synth.speak_text_async(prompt).get()
    assert result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted
    print("✅ Saved: " + output_file)
