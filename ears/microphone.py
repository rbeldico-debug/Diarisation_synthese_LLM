import queue
import sounddevice as sd
import numpy as np

class MicrophoneStream:
    """
    Gère l'ouverture du flux microphone via SoundDevice.
    Fournit un générateur pour récupérer les chunks audio séquentiellement.
    """
    def __init__(self, rate: int = 16000, block_size: int = 512):
        self.rate = rate
        self.block_size = block_size
        self._buff = queue.Queue()
        self.stream = None
        self.closed = True

    def __enter__(self):
        """Ouverture du contexte (avec le `with` statement)"""
        self.stream = sd.InputStream(
            samplerate=self.rate,
            blocksize=self.block_size,
            channels=1,
            dtype='float32',
            callback=self._callback
        )
        self.stream.start()
        self.closed = False
        print(f"Microphone ouvert : {self.rate}Hz, Block={self.block_size}")
        return self

    def __exit__(self, type, value, traceback):
        """Fermeture propre du flux"""
        if self.stream:
            self.stream.stop()
            self.stream.close()
        self.closed = True
        print("Microphone fermé.")

    def _callback(self, indata, frames, time, status):
        """Callback technique appelée par sounddevice (Thread séparé !)"""
        if status:
            print(f"Status Micro: {status}")
        # On met une copie des données dans la file d'attente
        self._buff.put(indata.copy())

    def generator(self):
        """
        Générateur qui yield les chunks audio.
        Bloque si pas de données, s'arrête si le flux est fermé.
        """
        while not self.closed:
            try:
                # Récupère un chunk (attend max 1s, sinon vérifie si fermé)
                chunk = self._buff.get(timeout=1.0)
                # Aplatir le chunk (de [512, 1] à [512])
                yield chunk.flatten()
            except queue.Empty:
                if self.closed:
                    break
                continue