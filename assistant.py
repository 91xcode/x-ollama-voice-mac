import sys
import json
import wave
import time
import pyttsx3
import torch
import requests
import soundfile
import yaml
import pygame
import pygame.locals
import numpy as np
import pyaudio
import whisper
import logging
import threading
import queue
import asyncio
import edge_tts
import os

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

BACK_COLOR = (0,0,0)
REC_COLOR = (255,0,0)
TEXT_COLOR = (255,255,255)
REC_SIZE = 80
FONT_SIZE = 24
WIDTH = 320
HEIGHT = 240
KWIDTH = 20
KHEIGHT = 6
MAX_TEXT_LEN_DISPLAY = 32

INPUT_DEFAULT_DURATION_SECONDS = 5
INPUT_FORMAT = pyaudio.paInt16
INPUT_CHANNELS = 1
INPUT_RATE = 16000
INPUT_CHUNK = 1024
OLLAMA_REST_HEADERS = {'Content-Type': 'application/json'}
INPUT_CONFIG_PATH ="assistant.yaml"

class Assistant:
    def __init__(self):
        logging.info("Initializing Assistant")
        self.config = self.init_config()
        
        # 预初始化 pygame mixer，避免每次语音播放时的初始化开销
        pygame.mixer.init()
        
        programIcon = pygame.image.load('assistant.png')

        self.clock = pygame.time.Clock()
        pygame.display.set_icon(programIcon)
        pygame.display.set_caption("Assistant")

        self.windowSurface = pygame.display.set_mode((WIDTH, HEIGHT), 0, 32)
        self.font = pygame.font.SysFont(None, FONT_SIZE)

        self.audio = pyaudio.PyAudio()

        # Initialize TTS engines
        self.tts_engine = pyttsx3.init()
        self.tts_engine.setProperty('rate', self.tts_engine.getProperty('rate') - 50)
        
        # Set default voice for edge-tts
        self.edge_voice = self.config.tts.edge_voice
        
        try:
            self.audio.open(format=INPUT_FORMAT,
                            channels=INPUT_CHANNELS,
                            rate=INPUT_RATE,
                            input=True,
                            frames_per_buffer=INPUT_CHUNK).close()
        except Exception as e:
            logging.error(f"Error opening audio stream: {str(e)}")
            self.wait_exit()

        self.display_message(self.config.messages.loadingModel)
        self.model = whisper.load_model(self.config.whisperRecognition.modelPath)
        self.context = []

        self.text_to_speech(self.config.conversation.greeting)
        time.sleep(0.5)
        self.display_message(self.config.messages.pressSpace)

    def wait_exit(self):
        while True:
            self.display_message(self.config.messages.noAudioInput)
            self.clock.tick(60)
            for event in pygame.event.get():
                if event.type == pygame.locals.QUIT:
                    self.shutdown()

    def shutdown(self):
        logging.info("Shutting down Assistant")
        self.audio.terminate()
        pygame.quit()
        sys.exit()

    def init_config(self):
        logging.info("Initializing configuration")
        class Inst:
            pass

        with open('assistant.yaml', encoding='utf-8') as data:
            configYaml = yaml.safe_load(data)

        config = Inst()
        config.messages = Inst()
        config.messages.loadingModel = configYaml["messages"]["loadingModel"]
        config.messages.pressSpace = configYaml["messages"]["pressSpace"]
        config.messages.noAudioInput = configYaml["messages"]["noAudioInput"]

        config.conversation = Inst()
        config.conversation.greeting = configYaml["conversation"]["greeting"]

        config.ollama = Inst()
        config.ollama.url = configYaml["ollama"]["url"]
        config.ollama.model = configYaml["ollama"]["model"]

        config.whisperRecognition = Inst()
        config.whisperRecognition.modelPath = configYaml["whisperRecognition"]["modelPath"]
        config.whisperRecognition.lang = configYaml["whisperRecognition"]["lang"]

        config.tts = Inst()
        config.tts.engine = configYaml["tts"]["engine"]  # 'edge-tts' or 'pyttsx3'
        config.tts.edge_voice = configYaml["tts"]["edge_voice"]

        return config

    def display_rec_start(self):
        logging.info("Displaying recording start")
        self.windowSurface.fill(BACK_COLOR)
        pygame.draw.circle(self.windowSurface, REC_COLOR, (WIDTH/2, HEIGHT/2), REC_SIZE)
        pygame.display.flip()

    def display_sound_energy(self, energy):
        logging.info(f"Displaying sound energy: {energy}")
        COL_COUNT = 5
        RED_CENTER = 100
        FACTOR = 10
        MAX_AMPLITUDE = 100

        self.windowSurface.fill(BACK_COLOR)
        amplitude = int(MAX_AMPLITUDE*energy)
        hspace, vspace = 2*KWIDTH, int(KHEIGHT/2)
        def rect_coords(x, y):
            return (int(x-KWIDTH/2), int(y-KHEIGHT/2),
                    KWIDTH, KHEIGHT)
        for i in range(-int(np.floor(COL_COUNT/2)), int(np.ceil(COL_COUNT/2))):
            x, y, count = WIDTH/2+(i*hspace), HEIGHT/2, amplitude-2*abs(i)

            mid = int(np.ceil(count/2))
            for i in range(0, mid):
                offset = i*(KHEIGHT+vspace)
                pygame.draw.rect(self.windowSurface, RED_CENTER,
                                rect_coords(x, y+offset))
                #mirror:
                pygame.draw.rect(self.windowSurface, RED_CENTER,
                                rect_coords(x, y-offset))
        pygame.display.flip()

    def display_message(self, text):
        logging.info(f"Displaying message: {text}")
        self.windowSurface.fill(BACK_COLOR)

        label = self.font.render(text
                                 if (len(text)<MAX_TEXT_LEN_DISPLAY)
                                 else (text[0:MAX_TEXT_LEN_DISPLAY]+"..."),
                                 1,
                                 TEXT_COLOR)

        size = label.get_rect()[2:4]
        self.windowSurface.blit(label, (WIDTH/2 - size[0]/2, HEIGHT/2 - size[1]/2))

        pygame.display.flip()

    def waveform_from_mic(self, key = pygame.K_SPACE) -> np.ndarray:
        logging.info("Capturing waveform from microphone")
        self.display_rec_start()

        stream = self.audio.open(format=INPUT_FORMAT,
                                 channels=INPUT_CHANNELS,
                                 rate=INPUT_RATE,
                                 input=True,
                                 frames_per_buffer=INPUT_CHUNK)
        frames = []

        while True:
            pygame.event.pump() # process event queue
            pressed = pygame.key.get_pressed()
            if pressed[key]:
                data = stream.read(INPUT_CHUNK)
                frames.append(data)
            else:
                break

        stream.stop_stream()
        stream.close()

        return np.frombuffer(b''.join(frames), np.int16).astype(np.float32) * (1 / 32768.0)

    def speech_to_text(self, waveform):
        logging.info("Converting speech to text")
        result_queue = queue.Queue()

        def transcribe_speech():
            try:
                logging.info("Starting transcription")
                transcript = self.model.transcribe(waveform,
                                                language=self.config.whisperRecognition.lang,
                                                fp16=torch.cuda.is_available())
                logging.info("Transcription completed")
                text = transcript["text"]
                print('\nMe:\n', text.strip())
                result_queue.put(text)
            except Exception as e:
                logging.error(f"An error occurred during transcription: {str(e)}")
                result_queue.put("")

        transcription_thread = threading.Thread(target=transcribe_speech)
        transcription_thread.start()
        transcription_thread.join()

        return result_queue.get()

    def ask_ollama(self, prompt, responseCallback):
        logging.info(f"Asking OLLaMa with prompt: {prompt}")
        full_prompt = prompt if hasattr(self, "contextSent") else (prompt)
        self.contextSent = True
        jsonParam = {
            "model": self.config.ollama.model,
            "stream": True,
            "context": self.context,
            "prompt": full_prompt
        }
        
        try:
            response = requests.post(self.config.ollama.url,
                                    json=jsonParam,
                                    headers=OLLAMA_REST_HEADERS,
                                    stream=True,
                                    timeout=30)
            response.raise_for_status()

            full_response = ""
            for line in response.iter_lines():
                if not line:
                    continue
                
                try:
                    body = json.loads(line)
                    token = body.get('response', '')
                    full_response += token

                    if 'error' in body:
                        logging.error(f"Error from OLLaMa: {body['error']}")
                        responseCallback("Error: " + body['error'])
                        return

                    if body.get('done', False) and 'context' in body:
                        self.context = body['context']
                        break
                except json.JSONDecodeError as e:
                    logging.error(f"Failed to decode JSON response: {str(e)}")
                    continue

            if full_response.strip():
                try:
                    responseCallback(full_response.strip())
                except Exception as e:
                    logging.error(f"Error in response callback: {str(e)}")
                    self.display_message("Error processing response")
            else:
                logging.warning("Received empty response from OLLaMa")
                self.display_message("Received empty response")

        except requests.exceptions.ReadTimeout as e:
            logging.error(f"ReadTimeout occurred while asking OLLaMa: {str(e)}")
            self.display_message("Request timed out. Please try again.")
        except requests.exceptions.RequestException as e:
            logging.error(f"An error occurred while asking OLLaMa: {str(e)}")
            self.display_message("Connection error. Please try again.")
        except Exception as e:
            logging.error(f"Unexpected error in ask_ollama: {str(e)}")
            self.display_message("An unexpected error occurred")

    async def edge_tts_speak(self, text):
        try:
            logging.info(f"Using edge-tts with voice: {self.edge_voice}")
            communicate = edge_tts.Communicate(text, self.edge_voice)
            
            # 使用异步方式并行处理音频生成
            audio_task = asyncio.create_task(communicate.save("temp_speech.mp3"))
            
            # 在音频生成的同时执行其他初始化
            if not pygame.mixer.get_init():
                pygame.mixer.init()
            
            # 等待音频生成完成
            await audio_task
            
            if not os.path.exists("temp_speech.mp3") or os.path.getsize("temp_speech.mp3") == 0:
                raise Exception("Generated audio file is empty or does not exist")
            
            pygame.mixer.music.load("temp_speech.mp3")
            pygame.mixer.music.play()
            
            while pygame.mixer.music.get_busy():
                await asyncio.sleep(0.1)  # 使用异步等待替代 pygame.time.wait
            
            # 不要每次都退出 mixer，只清理文件
            if os.path.exists("temp_speech.mp3"):
                os.remove("temp_speech.mp3")
            
        except Exception as e:
            logging.error(f"An error occurred during edge-tts speech playback: {str(e)}")
            logging.error(f"Voice being used: {self.edge_voice}")
            logging.info("Falling back to pyttsx3...")
            self.tts_engine.say(text)
            self.tts_engine.runAndWait()

    def text_to_speech(self, text):
        logging.info(f"Converting text to speech: {text}")
        print('\nAI:\n', text.strip())

        def play_speech():
            try:
                if self.config.tts.engine == "edge-tts":
                    # Create temp file for visualization
                    tempPath = './temp.wav'
                    
                    async def process_speech():
                        communicate = edge_tts.Communicate(text, self.edge_voice)
                        await communicate.save("temp_speech.mp3")
                        
                        # Convert mp3 to wav for visualization
                        data, samplerate = soundfile.read("temp_speech.mp3")
                        soundfile.write(tempPath, data, samplerate)
                        
                        # Play audio with visualization
                        wf = wave.open(tempPath, 'rb')
                        stream = self.audio.open(format=self.audio.get_format_from_width(wf.getsampwidth()),
                                              channels=wf.getnchannels(),
                                              rate=wf.getframerate(),
                                              output=True)
                        
                        chunkSize = 1024
                        chunk = wf.readframes(chunkSize)
                        while chunk:
                            stream.write(chunk)
                            tmp = np.array(np.frombuffer(chunk, np.int16), np.float32) * (1 / 32768.0)
                            energy_of_chunk = np.sqrt(np.mean(tmp**2))
                            self.display_sound_energy(energy_of_chunk)
                            chunk = wf.readframes(chunkSize)
                            
                        wf.close()
                        stream.stop_stream()
                        stream.close()
                        
                        # Cleanup temp files
                        if os.path.exists("temp_speech.mp3"):
                            os.remove("temp_speech.mp3")
                        if os.path.exists(tempPath):
                            os.remove(tempPath)
                    
                    asyncio.run(process_speech())
                    
                else:  # pyttsx3
                    tempPath = './temp.wav'
                    self.tts_engine.save_to_file(text, tempPath)
                    self.tts_engine.runAndWait()
                    
                    # Play audio with visualization
                    data, samplerate = soundfile.read(tempPath)
                    soundfile.write(tempPath, data, samplerate)
                    
                    wf = wave.open(tempPath, 'rb')
                    stream = self.audio.open(format=self.audio.get_format_from_width(wf.getsampwidth()),
                                          channels=wf.getnchannels(),
                                          rate=wf.getframerate(),
                                          output=True)
                    
                    chunkSize = 1024
                    chunk = wf.readframes(chunkSize)
                    while chunk:
                        stream.write(chunk)
                        tmp = np.array(np.frombuffer(chunk, np.int16), np.float32) * (1 / 32768.0)
                        energy_of_chunk = np.sqrt(np.mean(tmp**2))
                        self.display_sound_energy(energy_of_chunk)
                        chunk = wf.readframes(chunkSize)
                        
                    wf.close()
                    stream.stop_stream()
                    stream.close()
                    
                    if os.path.exists(tempPath):
                        os.remove(tempPath)
                
                logging.info("Speech playback completed")
                # self.display_message(text)
                
            except Exception as e:
                logging.error(f"An error occurred during speech playback: {str(e)}")

        # Use daemon thread so main program can exit
        speech_thread = threading.Thread(target=play_speech, daemon=True)
        speech_thread.start()


def main():
    logging.info("Starting Assistant")
    pygame.init()

    ass = Assistant()

    push_to_talk_key = pygame.K_SPACE
    quit_key = pygame.K_ESCAPE

    while True:
        ass.clock.tick(60)
        for event in pygame.event.get():
            if event.type == pygame.KEYDOWN:
                if event.key == push_to_talk_key:
                    logging.info("Push-to-talk key pressed")
                    speech = ass.waveform_from_mic(push_to_talk_key)

                    transcription = ass.speech_to_text(waveform=speech)

                    ass.ask_ollama(transcription, ass.text_to_speech)

                    time.sleep(1)
                    ass.display_message(ass.config.messages.pressSpace)

                elif event.key == quit_key:
                    logging.info("Quit key pressed")
                    ass.shutdown()


if __name__ == "__main__":
    main()
