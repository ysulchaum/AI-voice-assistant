import mysql.connector  # Import MySQL connector
from datetime import datetime

# MySQL configuration
db = mysql.connector.connect(
    host="localhost",
    user="root",  # Use environment variables
    password="yths114150",  # Use environment variables
    database="testing"
)

mycursor = db.cursor()

#mycursor.execute("CREATE TABLE conversations (id INT AUTO_INCREMENT PRIMARY KEY, user TEXT NOT NULL, ai TEXT NOT NULL, user_audio_filename TEXT, ai_audio_filename TEXT, timestamp DATETIME);")
# Insert query with a placeholder

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

def updateData(id, user, ai, user_audio_filename, ai_audio_filename, timestamp=datetime.now()):
    query = "UPDATE conversations SET user = %s, ai = %s, user_audio_filename = %s, ai_audio_filename = %s, timestamp = %s WHERE id = %s"
    values = (user, ai, user_audio_filename, ai_audio_filename, timestamp, id)
    mycursor.execute(query, values)
    db.commit()

def selectData():
    query = "SELECT * FROM conversations"
    mycursor.execute(query)
    for x in mycursor:
        print(x)

deleteData(1)