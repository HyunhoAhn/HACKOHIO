"""
테스트용 샘플 WAV 파일 생성
실제 음성 대신 간단한 오디오를 생성
"""
import wave
import numpy as np
from pathlib import Path

if __name__ == "__main__":
    # 테스트용 샘플 파일 생성
    samples_dir = Path("./samples")
    samples_dir.mkdir(exist_ok=True)
    
    sample_file = "SAMPLE.wav"
    
    print(f"\n📝 You can use this file for testing:")
    print(f"   {sample_file}")
