import os
import time
import whisper
import pyaudio
import wave
from openai import OpenAI
from elevenlabs.client import ElevenLabs
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import os  # Add this import
import mysql.connector  # Import MySQL connector
from datetime import datetime
import shutil

# API Keys
ELEVENLABS_API_KEY = "sk_6f50f8e0648155819f7664a8d83a5588f758c53c98a2a07e"
DEEPSEEK_API_KEY = "sk-42f8c04394a94ed38e893098d05a3a46"

# Initialize clients
client_elevenlabs = ElevenLabs(api_key=ELEVENLABS_API_KEY)
client_deepseek = OpenAI(api_key=DEEPSEEK_API_KEY,
                         base_url="https://api.deepseek.com")
model = whisper.load_model("base")

# MySQL configuration
db = mysql.connector.connect(
    host="localhost",
    user="root",  # Use environment variables
    password="yths114150",  # Use environment variables
    database="testing"
)

mycursor = db.cursor()

# ASR Module
def record_audio(filename="input.wav", sample_rate=16000, duration=5):
    chunk = 1024
    format = pyaudio.paInt16
    channels = 1
    rate = sample_rate
    audio = pyaudio.PyAudio()

    stream = audio.open(format=format, channels=channels,
                        rate=rate, input=True, frames_per_buffer=chunk)
    print("Recording... Speak now!")
    frames = []

    for _ in range(0, int(rate / chunk * duration)):
        data = stream.read(chunk)
        frames.append(data)

    print("Recording finished.")
    stream.stop_stream()
    stream.close()
    audio.terminate()

    # Save the recorded audio
    wf = wave.open(filename, "wb")
    wf.setnchannels(channels)
    wf.setsampwidth(audio.get_sample_size(format))
    wf.setframerate(rate)
    wf.writeframes(b''.join(frames))
    wf.close()
    return filename


def transcribe_audio(audio_file):
    result = model.transcribe(audio_file)
    return result["text"]

# return my voice in text
# need to send to the fnotend


def run_asr():
    print("Starting ASR module...")
    audio_file = record_audio("live_input.wav")
    text = transcribe_audio(audio_file)
    return text

# LLM Module
# return AI text
# need to send to the fnotend


def query_llm(input_text, model="deepseek-chat", max_tokens=100):
    try:
        response = client_deepseek.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are a helpful voice assistant."},
                {"role": "user", "content": input_text}
            ],
            stream=False
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"LLM Error: {e}")
        return "Sorry, I couldn't process that."

# TTS Module
# ouput AI voice from LLM
# need to send to the fnotend


def text_to_speech(text, output_file=None, voice="Rachel"):
    try:
        if output_file is None:
            output_file = fr"aiVoice\output_{int(time.time())}.mp3"
        audio_generator = client_elevenlabs.generate(
            text=text,
            voice=voice,
            model="eleven_monolingual_v1"
        )
        audio_bytes = b"".join(audio_generator)
        with open(output_file, "wb") as f:
            f.write(audio_bytes)

        print(f"Audio saved as {output_file}")

    except PermissionError as e:
        print(
            f"TTS Error: Permission denied ({e}). Try running as admin or freeing up '{output_file}'.")
    except Exception as e:
        print(f"TTS Error: {e}")

# Central Control Unit with Turn-Based Conversation


def run_assistant():
    print("Voice Assistant starting... Say 'exit' or 'quit' to stop.")
    n = True
    while n:
        # Step 1: ASR - Capture and transcribe speech
        try:
            asr_output = run_asr()
            print("You said:", asr_output)

            # Check for exit condition
            if asr_output.lower().strip() in ["exit", "quit"]:
                print("Assistant: Goodbye!")
                text_to_speech("Goodbye!")
                break
        except Exception as e:
            print(f"ASR Error: {e}")
            text_to_speech("Sorry, I couldn’t hear you. Let’s try again.")
            continue

        # Step 2: LLM - Process the input
        llm_response = query_llm(asr_output)
        print("Assistant text:", llm_response)

        # Step 3: TTS - Convert response to speech
        text_to_speech(llm_response)

        # Prompt for next turn
        # print("Waiting for your next input... Press spacebar to talk.")
        n = False

# clear the userVoice and aiVoice folder
def clear_folder(folder):
    for filename in os.listdir(folder):
        file_path = os.path.join(folder, filename)
        try:
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
        except Exception as e:
            print(f"Failed to delete {file_path}. Reason: {e}")



# Database functions
def insertData(id, user, ai, user_audio_filename, ai_audio_filename, timestamp=datetime.now()):
    query = "INSERT INTO conversations (id, user, ai, user_audio_filename, ai_audio_filename, timestamp) VALUES (%s, %s, %s, %s, %s, %s)"
    values = (id, user, ai, user_audio_filename, ai_audio_filename, timestamp)
    mycursor.execute(query, values)
    db.commit()

def deleteData(id):
    query = "DELETE FROM conversations WHERE id = %s"
    values = (id,)
    mycursor.execute(query, values)
    db.commit()

def deleteAllData():
    query = "DELETE FROM conversations"
    mycursor.execute(query)
    db.commit()

def updateData(id, user, ai, user_audio_filename, ai_audio_filename, timestamp=datetime.now()):
    query = "UPDATE conversations SET user = %s, ai = %s, user_audio_filename = %s, ai_audio_filename = %s, timestamp = %s WHERE id = %s"
    values = (user, ai, user_audio_filename, ai_audio_filename, timestamp, id)
    mycursor.execute(query, values)
    db.commit()
    
def getData(id, userOrAI="user"):
    query = "SELECT {} FROM conversations WHERE id = %s".format(userOrAI)
    values = (id,)
    mycursor.execute(query, values)
    result = mycursor.fetchone()
    return result

def selectData():
    query = "SELECT * FROM conversations"
    mycursor.execute(query)
    for x in mycursor:
        print(x)

def getTotalCount():
    query = "SELECT COUNT(*) FROM conversations"
    mycursor.execute(query)
    result = mycursor.fetchone()
    return result[0]




# Flask API

app = Flask(__name__)
CORS(app)


if getTotalCount() > 0:
    count = getTotalCount()
else:
    count = 0
response = None

@app.route('/process-audio', methods=['POST'])
def process_audio():
    global count  # Declare count as global
    if 'audio' not in request.files:
        return jsonify({'error': 'No audio file received'}), 400
    
    audio_file = request.files['audio']
    try:
        audio_content = audio_file.read()
        # Ensure the directory exists
        
        count += 1
        print(f"User voice received: userVoice_{count}.wav")
        
        output_dir = "userVoice"
        os.makedirs(output_dir, exist_ok=True)
        output_file = os.path.join(output_dir, f"userVoice_{count}.wav")  # Use .wav extension
        with open(output_file, "wb") as f:
            f.write(audio_content)
    except PermissionError as e:
        return jsonify({'error': f"Permission denied: {e}"}), 500
    except Exception as e:  # Catch other exceptions
        return jsonify({'error': str(e)}), 500
    
    # Sample processing
    transcript = transcribe_audio(output_file)
    global response
    response = query_llm(transcript)
    
    # Save AI voice
    try:
        text_to_speech(response, output_file=os.path.join("aiVoice", f"aiVoice_{count}.mp3"))
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
    # insert data to database
    try:
        insertData(count, transcript, response, f"userVoice_{count}.wav", f"aiVoice_{count}.mp3")
    except Exception as e:
        return jsonify({'error': str(e)}), 500

    
    return jsonify({
        'transcript': transcript,
        'response': response,
        'filenameUser': f"userVoice_{count}.wav",  # Add filename to response
        'filenameAI': f"aiVoice_{count}.mp3"  # Add filename to response
    })

# for getting the user audio
@app.route('/get-user-audio/<filename>', methods=['GET'])
def get_user_audio(filename):
    try:
        file_path = os.path.join("userVoice", filename)
        if not os.path.exists(file_path):
            return jsonify({'error': 'User Audio file not found'}), 404
        return send_file(file_path)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# for getting the AI audio
@app.route('/get-ai-audio/<filename>', methods=['GET'])
def get_ai_audio(filename):
    try:
        file_path = os.path.join("aiVoice", filename)
        if not os.path.exists(file_path):
            return jsonify({'error': 'AI audio file not found'}), 404
        return send_file(file_path)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
@app.route('/delete-all-conversations', methods=['DELETE'])
def delete_all_conversations():
    try:
        deleteAllData()
        clear_folder("userVoice")
        clear_folder("aiVoice")
        global count
        count = 0  # Reset the count
        return jsonify({'message': 'All conversations deleted successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
# to get the conversation history
@app.route('/get-history', methods=['GET'])
def get_history():
    aiListText = []
    userListText = []
    
    aiListVoice = []
    userListVoice = []
    try:
        for i in range(1, count + 1):
            # Get user and AI data
            aiListText.append(getData(i, "ai"))          
            userListText.append(getData(i, "user")) 
            
            aiListVoice.append(getData(i, "ai_audio_filename"))
            userListVoice.append(getData(i, "user_audio_filename"))
        return jsonify({
        'transcript': aiListText,
        'response': userListText,
        'filenameUser': userListVoice,  # Add filename to response
        'filenameAI': aiListVoice  # Add filename to response
    })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(port=5000)