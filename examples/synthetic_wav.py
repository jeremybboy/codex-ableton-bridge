"""Write a synthetic stereo PCM WAV for offline examples and tests."""
import argparse
import math
import struct
import wave


def write_wav(path, frequency=1000, amplitude=0.25, phase=0):
    sample_rate = 48000
    frames = bytearray()
    for index in range(sample_rate * 6):
        sample = round(32767 * amplitude * math.sin(math.tau * frequency * index / sample_rate + phase))
        frames.extend(struct.pack("<hh", sample, sample))
    with wave.open(str(path), "wb") as output:
        output.setnchannels(2)
        output.setsampwidth(2)
        output.setframerate(sample_rate)
        output.writeframes(frames)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", help="Destination for a six-second 1 kHz WAV")
    write_wav(parser.parse_args().path)
