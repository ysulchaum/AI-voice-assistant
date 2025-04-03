import "./App.css";
import { useState, useRef, useEffect } from "react";
import { FaMicrophone, FaMicrophoneSlash } from "react-icons/fa";

interface Message {
  speaker: "user" | "assistant";
  text: string;
  audioUrl?: string;
}

function App() {
  const [isRecording, setIsRecording] = useState(false);
  const [status, setStatus] = useState("Press the microphone to start");
  const [conversation, setConversation] = useState<Message[]>([]);

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);

  // Add useEffect to call getHistory when the app starts
  useEffect(() => {
    const abortController = new AbortController(); // Create AbortController
    getHistory(abortController.signal); // Pass signal to fetch

    return () => {
      abortController.abort(); // Abort fetch on unmount
    };// reason: prevent called twice
  }, []);

  const handleClear = async () => {
    const userConfirmed = window.confirm("Are you sure you want to clear?");
    if (userConfirmed) {
      // Add the logic to clear the content here
      try {
        await fetch("http://localhost:5000/delete-all-conversations", {
          method: "DELETE",
        });
        // Clear the UI conversation
        setConversation([]);
      } catch (error) {
        console.error("Error clearing content:", error);
        setStatus("Error: Content not cleared");
      }

      console.log("Content cleared!");
    } else {
      console.log("Clear action canceled.");
    }
  };

  const getHistory = async (signal?: AbortSignal) => {
    try {
      const response = await fetch("http://localhost:5000/get-history", {
        method: "GET",
        signal, // Attach signal to request
      });

      // Handle aborted request
      if (signal?.aborted) {
        console.log("Fetch aborted");
        return;
      }// reason: prevent called twice

      const data = await response.json();

      const aiTranscripts = data.transcript; // AI text list
      const userResponses = data.response; // User text list
      const userAudioFiles = data.filenameUser; // User audio filenames
      const aiAudioFiles = data.filenameAI; // AI audio filenames
      const count = aiTranscripts.length; // Number of messages

      for (let i = 0; i < count; i++) {
        // Fetch both audios
        const [userAudio, aiAudio] = await Promise.all([
          fetch(`http://localhost:5000/get-user-audio/${userAudioFiles[i]}`),
          fetch(`http://localhost:5000/get-ai-audio/${aiAudioFiles[i]}`),
        ]);

        // Create URLs
        const userAudioUrl = URL.createObjectURL(await userAudio.blob());
        const aiAudioUrl = URL.createObjectURL(await aiAudio.blob());

        // Add both messages to conversation
        setConversation((prev) => [
          ...prev,
          {
            speaker: "user",
            text: userResponses[i],
            audioUrl: userAudioUrl,
          },
          {
            speaker: "assistant",
            text: aiTranscripts[i],
            audioUrl: aiAudioUrl,
          },
        ]);
      }
    } catch (error: any) {
      if (error.name === "AbortError") {
        console.log("Request aborted");
      } else {
        console.error("Error fetching history:", error);
      }
    }
  };

  const toggleRecording = async () => {
    if (!isRecording) {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({
          audio: true,
        });
        const mediaRecorder = new MediaRecorder(stream);
        mediaRecorderRef.current = mediaRecorder;
        audioChunksRef.current = [];

        mediaRecorder.ondataavailable = (event: BlobEvent) => {
          audioChunksRef.current.push(event.data);
        };

        mediaRecorder.onstop = async () => {
          const audioBlob = new Blob(audioChunksRef.current, {
            type: "audio/wav",
          });
          const formData = new FormData();
          formData.append("audio", audioBlob, "recording.wav");

          try {
            setStatus("Processing...");
            const response = await fetch(
              "http://localhost:5000/process-audio",
              {
                method: "POST",
                body: formData,
              }
            );

            if (!response.ok) {
              const errorText = await response.text(); // Get raw response for debugging
              throw new Error(
                `Server error: ${response.status} - ${errorText}`
              );
            }

            const data = await response.json();

            // Fetch both audios
            const [userAudio, aiAudio] = await Promise.all([
              fetch(
                `http://localhost:5000/get-user-audio/${data.filenameUser}`
              ),
              fetch(`http://localhost:5000/get-ai-audio/${data.filenameAI}`),
            ]);

            // Create URLs
            const userAudioUrl = URL.createObjectURL(await userAudio.blob());
            const aiAudioUrl = URL.createObjectURL(await aiAudio.blob());

            // Add both messages to conversation
            setConversation((prev) => [
              ...prev,
              {
                speaker: "user",
                text: data.transcript,
                audioUrl: userAudioUrl,
              },
              {
                speaker: "assistant",
                text: data.response,
                audioUrl: aiAudioUrl,
              },
            ]);

            setStatus("Processing complete");
          } catch (error) {
            if (error instanceof Error) {
              console.error("Processing error:", error.message); // Log detailed error
            } else {
              console.error("Processing error:", error);
            }
            setStatus(
              `Error processing audio: ${
                error instanceof Error ? error.message : "Unknown error"
              }`
            );
          } finally {
            stream.getTracks().forEach((track) => track.stop());
          }
        };

        mediaRecorder.start();
        setIsRecording(true);
        setStatus("Recording... Speak now");
      } catch (error) {
        console.error("Error starting recording:", error);
        setStatus("Error: Microphone access denied");
      }
    } else {
      if (mediaRecorderRef.current) {
        mediaRecorderRef.current.stop();
        setIsRecording(false);
      }
    }
  };

  return (
    <div className="app-container">
      <header className="header">
        <h1>Voice Assistant</h1>
      </header>

      <main className="main-content">
        <div className="conversation-container">
          {conversation.map((message, index) => (
            <div
              key={index}
              className={`message ${
                message.speaker === "user"
                  ? "user-message"
                  : "assistant-message"
              }`}
            >
              <strong>
                {message.speaker === "user" ? "You:" : "Assistant:"}
              </strong>{" "}
              {message.text}
              {message.audioUrl && (
                <div className="audio-player">
                  <audio
                    controls
                    src={message.audioUrl}
                    onPlay={() => setStatus("Playing audio...")}
                    onEnded={() => setStatus("Audio finished")}
                  />
                </div>
              )}
            </div>
          ))}
        </div>

        <div className="controls">
          <button
            className={`mic-button ${isRecording ? "recording" : ""}`}
            onClick={toggleRecording}
            disabled={status === "Processing..."}
          >
            {isRecording ? <FaMicrophoneSlash /> : <FaMicrophone />}
          </button>
          <p className="status">{status}</p>

          <div className="function-bar">
            <button className="clear-button" onClick={handleClear}>
              Clear conversation
            </button>
          </div>
        </div>
      </main>

      <footer className="footer">
        <p>Powered by deepseek</p>
      </footer>
    </div>
  );
}

export default App;
