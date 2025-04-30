import os
import time
import whisper
import pyaudio
import wave
import requests
from openai import OpenAI
from elevenlabs.client import ElevenLabs
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import mysql.connector
from datetime import datetime
import shutil
import re
import json
from mem0 import MemoryClient
from huggingface_hub import InferenceClient
from PIL import Image
from autogen import ConversableAgent
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache

# API Keys
ELEVENLABS_API_KEY = "sk_c6bb12ac9fe4197a07ae0d9d69fa3d3662a8b40fd85d10fee"
DEEPSEEK_API_KEY = "sk-42f8c04394a94ed38e893098d05a3a46"
huggingface_api_key = "hf_igqqZtXtqhTHGhjlpRNIzGwoeGukvDksIxx"

# Initialize clients
client_elevenlabs = ElevenLabs(api_key=ELEVENLABS_API_KEY)
client_deepseek = OpenAI(api_key=DEEPSEEK_API_KEY,
                         base_url="https://api.deepseek.com")
model = whisper.load_model("tiny")  # Changed to tiny for faster transcription

memory_client = MemoryClient(
    api_key="m0-rlFtj1VTWE2DIjzxWfeqL4QHjgLdx3xxN97x2jQL")

# MySQL configuration
db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="yths114150",
    database="testing"
)

mycursor = db.cursor()

# Thread pool for parallel tasks
executor = ThreadPoolExecutor(max_workers=2)

# HuggingFace image generation
def huggingface_generate_image(prompt="An ai assistant"):
    client = InferenceClient(
        provider="fal-ai",
        api_key=huggingface_api_key
    )
    try:
        image = client.text_to_image(
            prompt=prompt,
            model="black-forest-labs/FLUX.1-dev",
            guidance_scale=7.5,
            negative_prompt="blurry, low quality, distorted, extra apples, unnatural colors",
            num_inference_steps=15,
            width=1024,
            height=512,
            scheduler="DDIM",
            seed=42
        )
        if isinstance(image, Image.Image):
            print("Image generated successfully!")
            output_path = "generated_image.png"
            image.save(output_path, "PNG")
            print(f"Image saved to {output_path}")
            return output_path
        else:
            print("Unexpected output type:", type(image))
            raise Exception("Image generation failed: Unexpected output type")
    except Exception as e:
        print("Error generating image:", str(e))
        raise e

def transcribe_audio(audio_file):
    print(f"Transcribing audio: {audio_file}")
    result = model.transcribe(audio_file)
    return result["text"]

# LLM Image Prompt Generation
def query_llm_image_prompt(input_text, model="deepseek-chat", max_tokens=100):
    try:
        if not isinstance(input_text, str) or not input_text.strip():
            print(f"Invalid input_text: {input_text}, using default prompt")
            return "A friendly AI assistant in a futuristic setting"
        messages = [
            {"role": "system", "content": "You are an image prompt engineer."},
            {"role": "system", "content": "Your mission is to create a detailed and imaginative prompt for an AI image generator according to the user's input."},
            {"role": "system", "content": "You only need to provide the prompt without any additional text and keep the prompt simple."},
            {"role": "system", "content": "As the user input should be a simple conversation, you should analyze the user input and create a prompt."},
            {"role": "user", "content": input_text}
        ]
        response = client_deepseek.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=max_tokens,
            stream=False
        )
        raw_response = response.choices[0].message.content.strip()
        return raw_response
    except Exception as e:
        print(f"LLM Error: {e}")
        return "A red AI assistant."

# Initialize memory
def init_memory(USER_ID="Tom", AGENT_ID="May"):
    system_messages = [
        {"role": "system",
         "content": f"You are a friendly assistant. Avoid action descriptions."},
        {"role": "system", "content": "Use simple natural spoken words only—no action descriptions."},
        {"role": "system", "content": "Keep your response simple, short, and like a daily chatting conversation."},
    ]
    try:
        print("Adding initial memory...")
        response = memory_client.add(
            messages=system_messages,
            user_id=USER_ID,
            agent_id=AGENT_ID
        )
        print("Add response:", response)
    except Exception as e:
        print("Mem0 Error:", e)

# Cache LLM responses
@lru_cache(maxsize=100)
def cached_query_llm(input_text, USER_ID="Tom", AGENT_ID="May", model="deepseek-chat", max_tokens=50):
    return query_llm(input_text, USER_ID, AGENT_ID, model, max_tokens)

# Updated query_llm with ConversableAgent
def query_llm(input_text, USER_ID="Tom", AGENT_ID="May", model="deepseek-chat", max_tokens=50):
    print(f"Querying LLM with input: {input_text}")
    try:
        if not isinstance(input_text, str) or not input_text.strip():
            return "Sorry, I couldn't understand your input."

        # Search for relevant memories
        relevant_memories = memory_client.search(
            query=input_text, user_id=USER_ID, agent_id=AGENT_ID)
        print("Search results:", relevant_memories)

        # Extract memory content
        context = "\n".join([m.get("memory", "") for m in relevant_memories])

        # Configure ConversableAgent
        llm_config = {
            "model": model,
            "api_key": DEEPSEEK_API_KEY,
            "base_url": "https://api.deepseek.com",
            "max_tokens": max_tokens
        }

        assistant = ConversableAgent(
            name=AGENT_ID,
            system_message=f"You are You are a friendly assistant. Context: {context}",
            llm_config=llm_config,
            human_input_mode="NEVER"
        )

        # Generate response
        prompt = f"User: {input_text}\n{AGENT_ID}:"
        response = assistant.generate_reply(messages=[{"content": prompt, "role": "user"}])

        # Validate response
        if not response:
            print("Agent returned empty response")
            return "Sorry, I couldn't generate a response."

        # Store conversation in memory
        conversation = [
            {"role": "user", "content": input_text},
            {"role": "assistant", "content": response}
        ]
        try:
            memory_response = memory_client.add(
                messages=conversation,
                user_id=USER_ID,
                agent_id=AGENT_ID
            )
            print("Stored conversation memory:", memory_response)
        except Exception as e:
            print("Mem0 Store Error:", e)

        # Clean response
        clean_response = re.sub(r'\*+[^*]+\*+', '', response).replace('  ', ' ').strip()
        return clean_response

    except requests.exceptions.RequestException as e:
        print(f"LLM API Network Error: {e}")
        return "Sorry, I'm having trouble connecting right now."
    except ValueError as e:
        print(f"LLM Response Error: {e}")
        return "Sorry, I couldn't process that."
    except Exception as e:
        print(f"Unexpected LLM Error: {e}")
        return "Sorry, something went wrong."

# TTS Module
def text_to_speech(text, output_file=None, voice="Rachel"):
    print(f"Generating TTS for text: {text}")
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
        print(f"TTS Error: Permission denied ({e}). Try running as admin or freeing up '{output_file}'.")
    except Exception as e:
        print(f"TTS Error: {e}")

# Clear folder
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
    print(f"Inserting data: id={id}, user={user}, ai={ai}, user_audio={user_audio_filename}, ai_audio={ai_audio_filename}")
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

@app.route('/process-input', methods=['POST'])
def process_input():
    global count
    count += 1
    user_input = None
    user_audio_filename = None
    ai_audio_filename = f"aiVoice_{count}.mp3"

    try:
        # Check if input is audio (multipart/form-data)
        if 'audio' in request.files:
            audio_file = request.files['audio']
            audio_content = audio_file.read()
            print(f"User voice received: userVoice_{count}.wav")
            output_dir = "userVoice"
            os.makedirs(output_dir, exist_ok=True)
            user_audio_filename = f"userVoice_{count}.wav"
            output_file = os.path.join(output_dir, user_audio_filename)
            with open(output_file, "wb") as f:
                f.write(audio_content)
            user_input = transcribe_audio(output_file)
        # Check if input is text (JSON)
        elif request.is_json:
            data = request.get_json()
            if not data or 'text' not in data:
                return jsonify({'error': 'No text provided'}), 400
            user_input = data['text']
        else:
            return jsonify({'error': 'Invalid input: Expected audio or JSON text'}), 400

        # Parallelize LLM and TTS
        def get_llm_response():
            return cached_query_llm(user_input)

        def generate_tts(response):
            text_to_speech(response, output_file=os.path.join("aiVoice", ai_audio_filename))

        # Execute LLM and TTS in parallel
        llm_future = executor.submit(get_llm_response)
        response = llm_future.result()
        tts_future = executor.submit(generate_tts, response)
        tts_future.result()  # Wait for TTS to complete

        insertData(count, user_input, response, user_audio_filename, ai_audio_filename)

        # Build response
        response_data = {
            'transcript': user_input,
            'response': response,
            'filenameAI': ai_audio_filename
        }
        if user_audio_filename:
            response_data['filenameUser'] = user_audio_filename

        print(f"Returning response: {response_data}")
        return jsonify(response_data)

    except PermissionError as e:
        print(f"Permission error: {e}")
        return jsonify({'error': f"Permission denied: {e}"}), 500
    except Exception as e:
        print(f"Unexpected error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/get-user-audio/<filename>', methods=['GET'])
def get_user_audio(filename):
    try:
        file_path = os.path.join("userVoice", filename)
        if not os.path.exists(file_path):
            return jsonify({'error': 'User Audio file not found'}), 404
        return send_file(file_path)
    except Exception as e:
        print(f"Error getting user audio: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/get-ai-audio/<filename>', methods=['GET'])
def get_ai_audio(filename):
    try:
        file_path = os.path.join("aiVoice", filename)
        if not os.path.exists(file_path):
            return jsonify({'error': 'AI audio file not found'}), 404
        return send_file(file_path)
    except Exception as e:
        print(f"Error getting AI audio: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/generate-image', methods=['GET'])
def generate_image_route():
    try:
        prompt_input = "A friendly AI assistant"
        if count > 0:
            ai_data = getData(count, "ai")
            print(f"getData(count, 'ai') returned: {ai_data}")
            if ai_data and ai_data[0]:
                prompt_input = ai_data[0]
        prompt = query_llm_image_prompt(prompt_input)
        print(f"Generated prompt: {prompt}")
        image_path = huggingface_generate_image(prompt)
        return send_file(image_path, mimetype='image/png')
    except Exception as e:
        print(f"Error generating image: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/delete-all-conversations', methods=['DELETE'])
def delete_all_conversations():
    try:
        deleteAllData()
        clear_folder("userVoice")
        clear_folder("aiVoice")
        global count
        count = 0
        return jsonify({'message': 'All conversations deleted successfully'})
    except Exception as e:
        print(f"Error deleting conversations: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/get-history', methods=['GET'])
def get_history():
    aiListText = []
    userListText = []
    aiListVoice = []
    userListVoice = []
    try:
        for i in range(1, count + 1):
            ai_data = getData(i, "ai")
            user_data = getData(i, "user")
            ai_audio = getData(i, "ai_audio_filename")
            user_audio = getData(i, "user_audio_filename")
            aiListText.append(ai_data[0] if ai_data else "")
            userListText.append(user_data[0] if user_data else "")
            aiListVoice.append(ai_audio[0] if ai_audio else "")
            userListVoice.append(user_audio[0] if user_audio else "")
        response_data = {
            'transcript': aiListText,
            'response': userListText,
            'filenameUser': userListVoice,
            'filenameAI': aiListVoice
        }
        print(f"Returning history: {response_data}")
        return jsonify(response_data)
    except Exception as e:
        print(f"Error getting history: {e}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(port=5000)
