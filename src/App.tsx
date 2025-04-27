import "./App.css";
import { useState, useRef, useEffect } from "react";
import { FaMicrophone, FaMicrophoneSlash } from "react-icons/fa";
import { v4 as uuidv4 } from "uuid";

interface Message {
  id: string;
  speaker: "user" | "assistant";
  text: string;
  audioUrl?: string;
}

function App() {
  const [isRecording, setIsRecording] = useState(false);
  const [status, setStatus] = useState("Press the microphone to start");
  const [conversation, setConversation] = useState<Message[]>([]);
  const [image, setImage] = useState<string | null>(null);
  const [textInput, setTextInput] = useState("");
  const conversationContainerRef = useRef<HTMLDivElement>(null);

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);

  // Scroll to the bottom of the conversation
  useEffect(() => {
    if (conversationContainerRef.current) {
      conversationContainerRef.current.scrollTop =
        conversationContainerRef.current.scrollHeight;
    }
  }, [conversation]);

  // Fetch history on mount
  useEffect(() => {
    const abortController = new AbortController();
    getHistory(abortController.signal);
    return () => {
      abortController.abort();
    };
  }, []);

  const handleSendText = async () => {
    if (!textInput.trim()) {
      setStatus("Error: Please enter some text");
      return;
    }

    const userMessage: Message = {
      id: uuidv4(),
      speaker: "user",
      text: textInput,
    };
    setConversation((prev) => [...prev, userMessage]);
    setTextInput("");
    setStatus("Processing text...");

    try {
      const response = await fetch("http://localhost:5000/process-input", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ text: textInput }),
      });

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`Server error: ${response.status} - ${errorText}`);
      }

      const data = await response.json();
      // Preload AI audio
      const aiAudioPromise = fetch(
        `http://localhost:5000/get-ai-audio/${data.filenameAI}`
      ).then((res) => res.blob());
      const aiAudioBlob = await aiAudioPromise;
      const aiAudioUrl = URL.createObjectURL(aiAudioBlob);

      const aiMessage: Message = {
        id: uuidv4(),
        speaker: "assistant",
        text: data.response,
        audioUrl: aiAudioUrl,
      };
      setConversation((prev) => [...prev, aiMessage]);
      setStatus("Text processed successfully");
    } catch (error) {
      console.error("Error processing text:", error);
      setStatus(
        `Error processing text: ${
          error instanceof Error ? error.message : "Unknown error"
        }`
      );
    }
  };

  const handleImage = async () => {
    try {
      const response = await fetch("http://localhost:5000/generate-image", {
        method: "GET",
      });
      if (!response.ok) {
        throw new Error("Failed to fetch image");
      }
      const data = await response.blob();
      const imageUrl = URL.createObjectURL(data);
      setImage(imageUrl);
    } catch (error) {
      console.error("Error fetching image:", error);
    }
  };

  const handleClear = async () => {
    const userConfirmed = window.confirm("Are you sure you want to clear?");
    if (userConfirmed) {
      try {
        await fetch("http://localhost:5000/delete-all-conversations", {
          method: "DELETE",
        });
        setConversation([]);
        setImage(null);
        handleImage();
      } catch (error) {
        console.error("Error clearing content:", error);
        setStatus("Error: Content not cleared");
      }
    }
  };

  const getHistory = async (signal?: AbortSignal) => {
    try {
      const response = await fetch("http://localhost:5000/get-history", {
        method: "GET",
        signal,
      });
      if (signal?.aborted) {
        console.log("Fetch aborted");
        return;
      }
      const data = await response.json();

      const aiTranscripts = data.transcript;
      const userResponses = data.response;
      const userAudioFiles = data.filenameUser;
      const aiAudioFiles = data.filenameAI;
      const count = aiTranscripts.length;

      const newConversation: Message[] = [];
      for (let i = 0; i < count; i++) {
        let userAudioUrl: string | undefined;
        let aiAudioUrl: string | undefined;

        if (userAudioFiles[i]) {
          const userAudio = await fetch(
            `http://localhost:5000/get-user-audio/${userAudioFiles[i]}`
          );
          userAudioUrl = URL.createObjectURL(await userAudio.blob());
        }
        if (aiAudioFiles[i]) {
          const aiAudio = await fetch(
            `http://localhost:5000/get-ai-audio/${aiAudioFiles[i]}`
          );
          aiAudioUrl = URL.createObjectURL(await aiAudio.blob());
        }

        newConversation.push({
          id: uuidv4(),
          speaker: "user",
          text: userResponses[i] || "",
          audioUrl: userAudioUrl,
        });
        newConversation.push({
          id: uuidv4(),
          speaker: "assistant",
          text: aiTranscripts[i] || "",
          audioUrl: aiAudioUrl,
        });
      }

      setConversation(newConversation);
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

          setStatus("Processing audio...");
          try {
            const response = await fetch(
              "http://localhost:5000/process-input",
              {
                method: "POST",
                body: formData,
              }
            );

            if (!response.ok) {
              const errorText = await response.text();
              throw new Error(
                `Server error: ${response.status} - ${errorText}`
              );
            }

            const data = await response.json();

            const userMessage: Message = {
              id: uuidv4(),
              speaker: "user",
              text: data.transcript,
              audioUrl: data.filenameUser
                ? URL.createObjectURL(
                    await (
                      await fetch(
                        `http://localhost:5000/get-user-audio/${data.filenameUser}`
                      )
                    ).blob()
                  )
                : undefined,
            };
            setConversation((prev) => [...prev, userMessage]);

            // Preload AI audio
            const aiAudioPromise = fetch(
              `http://localhost:5000/get-ai-audio/${data.filenameAI}`
            ).then((res) => res.blob());
            const aiAudioBlob = await aiAudioPromise;
            const aiAudioUrl = URL.createObjectURL(aiAudioBlob);

            const aiMessage: Message = {
              id: uuidv4(),
              speaker: "assistant",
              text: data.response,
              audioUrl: aiAudioUrl,
            };
            setConversation((prev) => [...prev, aiMessage]);

            setStatus("Processing complete");
          } catch (error) {
            console.error("Error processing audio:", error);
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
      <div className="left-side">
        <h1 className="title">Voice Assistant</h1>
        <div className="image-container">
          <img
            src={image || "./background.png"}
            alt="Assistant"
            className="assistant-image"
          />
        </div>
        <div className="control-container">
          <button className="clear-button" onClick={handleClear}>
            Clear
          </button>
          <button
            className={`mic-button ${isRecording ? "recording" : ""}`}
            onClick={toggleRecording}
            disabled={status === "Processing..."}
          >
            {isRecording ? (
              <FaMicrophoneSlash size={24} color="#fff" />
            ) : (
              <FaMicrophone size={24} color="#fff" />
            )}
          </button>
        </div>
        <p className="status">{status}</p>
      </div>

      <div className="right-side">
        <div className="conversation-container" ref={conversationContainerRef}>
          {conversation.map((message) => (
            <div
              key={message.id}
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
        <div className="typewriter-container">
          <textarea
            className="text-input"
            value={textInput}
            onChange={(e) => setTextInput(e.target.value)}
            placeholder="Type your message here..."
          />
          <button className="send-button" onClick={handleSendText}>
            Send
          </button>
        </div>
      </div>
    </div>
  );
}

export default App;