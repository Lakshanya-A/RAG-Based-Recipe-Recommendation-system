// import "./App.css";
import React, { useState, useRef, useEffect } from "react";

function App() {
  const [messages, setMessages] = useState([]);
  const [inputText, setInputText] = useState("");
  const [isListening, setIsListening] = useState(false);
  const messagesEndRef = useRef(null);
  const recognitionRef = useRef(null);

  useEffect(() => {
    // Initialize speech recognition
    if ('webkitSpeechRecognition' in window) {
      recognitionRef.current = new window.webkitSpeechRecognition();
      recognitionRef.current.continuous = false;
      recognitionRef.current.interimResults = false;
      recognitionRef.current.lang = 'en-US';

      recognitionRef.current.onresult = (event) => {
        const transcript = event.results[0][0].transcript;
        setInputText(transcript);
      };

      recognitionRef.current.onerror = (event) => {
        console.error('Speech recognition error:', event.error);
        setIsListening(false);
      };

      recognitionRef.current.onend = () => {
        setIsListening(false);
      };
    } else {
      console.error('Speech recognition not supported');
    }

    return () => {
      if (recognitionRef.current) {
        recognitionRef.current.stop();
      }
    };
  }, []);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!inputText.trim()) return;

    // Add user message
    const userMessage = { text: inputText, sender: "user" };
    setMessages(prev => [...prev, userMessage]);
    setInputText("");

    try {
      const res = await fetch(`/api/chat`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ message: inputText }),
      });
      
      if (!res.ok) {
        throw new Error(`HTTP error! status: ${res.status}`);
      }
      
      const data = await res.json();
      
      if (!data.response) {
        throw new Error('No response from server');
      }

      // Add bot response
      const botMessage = { text: data.response, sender: "bot" };
      setMessages(prev => [...prev, botMessage]);
    } catch (err) {
      console.error('Error:', err);
      // Add error message
      const errorMessage = { 
        text: "Sorry, I couldn't process your request at the moment. Please try again.", 
        sender: "bot" 
      };
      setMessages(prev => [...prev, errorMessage]);
    }
  };

  const toggleVoiceInput = () => {
    if (!recognitionRef.current) {
      alert('Speech recognition is not supported in your browser.');
      return;
    }

    if (isListening) {
      recognitionRef.current.stop();
    } else {
      try {
        recognitionRef.current.start();
        setIsListening(true);
      } catch (error) {
        console.error('Error starting speech recognition:', error);
        setIsListening(false);
      }
    }
  };

  React.useEffect(() => {
    scrollToBottom();
  }, [messages]);

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900">
      <div className="max-w-4xl mx-auto px-4 py-8">
        <div className="flex items-center justify-center mb-8">
          <img 
            src="https://www.gstatic.com/lamda/images/gemini_sparkle_v002_d4735304ff6292a690345.svg" 
            alt="Gemini" 
            className="w-12 h-12 mr-4"
          />
          <h1 className="text-3xl font-bold text-white">
            Recipe Assistant
          </h1>
        </div>

        <div className="bg-white/5 backdrop-blur-lg rounded-2xl shadow-xl overflow-hidden">
          <div className="h-[70vh] overflow-y-auto p-6 space-y-6">
            {messages.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-full text-gray-400">
                <img 
                  src="https://www.gstatic.com/lamda/images/gemini_sparkle_v002_d4735304ff6292a690345.svg" 
                  alt="Gemini" 
                  className="w-16 h-16 mb-4 opacity-50"
                />
                <p className="text-lg">What would you like to cook today?</p>
                <p className="text-sm mt-2 text-gray-500">Try asking for recipes with specific ingredients!</p>
              </div>
            ) : (
              messages.map((message, index) => (
                <div
                  key={index}
                  className={`flex ${message.sender === "user" ? "justify-end" : "justify-start"}`}
                >
                  {message.sender === "bot" && (
                    <img 
                      src="https://www.gstatic.com/lamda/images/gemini_sparkle_v002_d4735304ff6292a690345.svg" 
                      alt="Gemini" 
                      className="w-8 h-8 mr-3 mt-1"
                    />
                  )}
                  <div
                    className={`max-w-[80%] rounded-2xl p-4 ${
                      message.sender === "user"
                        ? "bg-blue-600 text-white ml-12"
                        : "bg-gray-800/50 text-white mr-12"
                    }`}
                  >
                    {message.text.split('\n').map((line, i) => (
                      <React.Fragment key={i}>
                        {line}
                        {i < message.text.split('\n').length - 1 && <br />}
                      </React.Fragment>
                    ))}
                  </div>
                </div>
              ))
            )}
            <div ref={messagesEndRef} />
          </div>

          <form onSubmit={handleSubmit} className="p-4 border-t border-gray-700/50">
            <div className="flex space-x-3">
              <input
                type="text"
                value={inputText}
                onChange={(e) => setInputText(e.target.value)}
                placeholder="Ask for recipes with ingredients..."
                className="flex-1 bg-gray-800/50 text-white rounded-xl px-4 py-3 focus:outline-none focus:ring-2 focus:ring-blue-500 placeholder-gray-400"
              />
              <button
                type="button"
                onClick={toggleVoiceInput}
                className={`p-3 rounded-xl ${
                  isListening ? "bg-red-600 animate-pulse" : "bg-gray-800/50"
                } hover:bg-gray-700/50 transition-colors`}
                title={isListening ? "Stop listening" : "Start voice input"}
              >
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  className="h-6 w-6"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z"
                  />
                </svg>
              </button>
              <button
                type="submit"
                className="bg-blue-600 text-white px-6 py-3 rounded-xl hover:bg-blue-700 transition-colors font-medium"
              >
                Send
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}

export default App;
