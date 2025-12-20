import os
import numpy as np
from scipy.io import wavfile

from ears.microphone import MicrophoneStream
from ears.vad_engine import VADSegmenter


def save_wav(filename, data, rate):
    # Convertir float32 -> int16 pour lecture facile par lecteur média standard
    data_int16 = (data * 32767).astype(np.int16)
    wavfile.write(filename, rate, data_int16)
    print(f"💾 Sauvegardé : {filename}")


def main():
    # Configuration
    SAMPLE_RATE = 16000
    BLOCK_SIZE = 512  # Correspond souvent à une fenêtre de ~30ms

    # Création dossier de sortie
    output_dir = "test_segments"
    os.makedirs(output_dir, exist_ok=True)

    print("--- TEST STEP 1 : VALIDATION VAD ---")
    print(f"Les segments détectés seront sauvegardés dans '{output_dir}/'")
    print("Parlez dans le micro. (Ctrl+C pour arrêter)")

    vad = VADSegmenter(sample_rate=SAMPLE_RATE)
    segment_count = 0

    try:
        with MicrophoneStream(rate=SAMPLE_RATE, block_size=BLOCK_SIZE) as mic:
            for chunk in mic.generator():

                # Envoi à la VAD
                payload = vad.process_chunk(chunk)

                # Si la VAD renvoie quelque chose, c'est qu'une phrase est finie
                if payload:
                    segment_count += 1
                    filename = f"{output_dir}/phrase_{segment_count:03d}.wav"
                    save_wav(filename, payload.audio_data, payload.sample_rate)
                    print(f"Fin de phrase détectée ! Durée : {payload.duration_seconds:.2f}s")

    except KeyboardInterrupt:
        print("\nArrêt du test.")


if __name__ == "__main__":
    main()