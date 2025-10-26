import unittest
import pronunciation_assessment


class TestPronunciationAssessment(unittest.TestCase):
    def test_assessment(self):
        test_wav_file = "./test_wav/test_wav.wav"
        reference_text = "9 + 7 equals"

        result = pronunciation_assessment.pronunciation_assessment(test_wav_file, reference_text)
        print(result)
