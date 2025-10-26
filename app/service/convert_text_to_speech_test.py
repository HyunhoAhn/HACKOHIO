import unittest
import convert_text_to_speech


class TestPronunciationAssessment(unittest.TestCase):
    def test_assessment(self):
        test_wav_file_name = "test.wav"
        reference_text = "9 + 7 equals"

        result = convert_text_to_speech.convert_text_to_speech(reference_text, test_wav_file_name)
        print(result)
