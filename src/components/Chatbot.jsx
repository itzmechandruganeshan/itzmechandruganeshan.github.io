import Draggable from "react-draggable"
import { motion, AnimatePresence } from "framer-motion"
import { BiMessageSquareDetail } from "react-icons/bi"
import { FaRobot } from "react-icons/fa"
import { IoClose } from "react-icons/io5"
import { useState, useEffect, useRef } from "react"
import { FiSend } from "react-icons/fi"
import { BsFillPersonFill } from "react-icons/bs"

const Chatbot = () => {
  const [isOpen, setIsOpen] = useState(false)
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState("")
  const [botTyping, setBotTyping] = useState(false)
  const chatContentRef = useRef(null)
  const socketRef = useRef(null)

  const toggleChatbot = () => setIsOpen(!isOpen)

  // Connect to the WebSocket
  const connectWebSocket = () => { wss://hostile-mireille-cloudsidee-6fcc2a35.koyeb.app/ws
    socketRef.current = new WebSocket("YOUR CONNECTION URL")

    socketRef.current.onopen = () => {
      console.log("WebSocket Connected")
    }

    socketRef.current.onmessage = (event) => {
      const message = event.data
      setMessages((prevMessages) => [...prevMessages, { text: message, sender: "bot", timestamp: new Date() }])
      setBotTyping(false)
    }

    socketRef.current.onclose = () => {
      console.log("WebSocket Disconnected")
    }

    socketRef.current.onerror = (error) => {
      console.log("WebSocket Error: ", error)
    }
  }

  const sendMessage = () => {
    if (input.trim()) {
      const newMessages = [...messages, { text: input, sender: "user", timestamp: new Date() }]
      setMessages(newMessages)
      setInput("")

      // Send the message through WebSocket
      if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
        socketRef.current.send(input)
        setBotTyping(true)
      }
    }
  }

  const handleKeyDown = (e) => {
    if (e.key === "Enter") sendMessage()
  }

  // Auto-scroll to the bottom of the chat when new messages are added
  useEffect(() => {
    if (chatContentRef.current) {
      chatContentRef.current.scrollTop = chatContentRef.current.scrollHeight
    }
  }, [messages]) // Removed botTyping from dependencies

  useEffect(() => {
    if (isOpen) {
      connectWebSocket()
    } else if (socketRef.current) {
      socketRef.current.close()
    }

    return () => {
      if (socketRef.current) socketRef.current.close()
    }
  }, [isOpen])

  return (
    <div>
      {/* Chat Message Icon */}
      <motion.div
        className="fixed bottom-8 right-8 p-3 bg-gradient-to-br from-indigo-600 to-purple-800 rounded-full cursor-pointer shadow-lg z-50"
        whileHover={{ scale: 1.1, rotate: 5 }}
        onClick={toggleChatbot}
        style={{
          background: "linear-gradient(145deg, #7F5FFF, #604FCB)",
          boxShadow: "0 4px 10px rgba(0, 0, 0, 0.2), inset 0px 1px 2px rgba(255, 255, 255, 0.3)",
        }}
      >
        <BiMessageSquareDetail color="white" size={24} />
      </motion.div>

      {/* Chatbot Window */}
      <AnimatePresence>
        {isOpen && (
          <Draggable handle=".chatbot-header">
            <motion.div
              className="fixed bottom-20 right-4 w-80 sm:w-96 bg-opacity-70 rounded-lg shadow-2xl backdrop-blur-lg overflow-hidden z-40"
              initial={{ opacity: 0, y: 50, scale: 0.9 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: 50, scale: 0.9 }}
              transition={{ duration: 0.4, ease: "easeInOut" }}
              style={{
                background: "rgba(255, 255, 255, 0.1)",
                borderRadius: "20px",
                boxShadow: "0 8px 32px rgba(31, 38, 135, 0.37)",
                border: "1px solid rgba(255, 255, 255, 0.18)",
              }}
            >
              {/* Header */}
              <div className="flex items-center justify-between px-4 py-3 bg-gradient-to-r from-purple-700 via-purple-500 to-purple-800 text-white rounded-t-lg chatbot-header cursor-move">
                <div className="flex items-center space-x-2">
                  <FaRobot className="bg-white bg-opacity-20 rounded-full p-1" size={24} />
                  <h3 className="text-lg font-semibold">Chandru Ganeshan</h3>
                </div>
                <motion.div whileHover={{ scale: 1.1 }} whileTap={{ scale: 0.9 }}>
                  <IoClose
                    size={20}
                    className="cursor-pointer hover:text-red-500 transition duration-150"
                    onClick={toggleChatbot}
                  />
                </motion.div>
              </div>

              {/* Chat Content */}
              <div
                ref={chatContentRef}
                className="p-4 h-96 overflow-y-auto text-sm text-neutral-100 space-y-4"
                style={{
                  scrollbarWidth: "none", // Hides scrollbar for Firefox
                  msOverflowStyle: "none", // Hides scrollbar for IE and Edge
                }}
              >
                <style>{`
                  /* Hides scrollbar for Chrome, Safari, and Edge */
                  .p-4::-webkit-scrollbar {
                    display: none;
                  }
                `}</style>
                {messages.length === 0 ? (
                  <p className="text-center text-neutral-500">Ask me anything!</p>
                ) : (
                  messages.map((message, index) => (
                    <motion.div
                      key={index}
                      initial={{ opacity: 0, x: message.sender === "user" ? 20 : -20, y: 20 }}
                      animate={{ opacity: 1, x: 0, y: 0 }}
                      transition={{ duration: 0.3, type: "spring" }}
                      className={`flex flex-col ${message.sender === "user" ? "items-end" : "items-start"}`}
                    >
                      <div
                        className={`flex items-center space-x-2 ${
                          message.sender === "user" ? "justify-end" : "justify-start"
                        }`}
                      >
                        {message.sender === "bot" ? (
                          <FaRobot className="text-purple-400 bg-white bg-opacity-10 rounded-full p-1" size={18} />
                        ) : (
                          <BsFillPersonFill className="text-blue-400" size={18} />
                        )}
                        <div
                          className={`px-4 py-2 rounded-lg ${
                            message.sender === "user"
                              ? "bg-gradient-to-r from-indigo-500 to-blue-600 text-white shadow-lg"
                              : "bg-neutral-700 text-neutral-200 shadow-md"
                          }`}
                          style={{
                            border: message.sender === "bot" ? "1px solid rgba(255, 255, 255, 0.1)" : "none",
                          }}
                        >
                          {message.text}
                        </div>
                      </div>
                      <span className="text-xs text-neutral-500 mt-1">
                        {message.timestamp.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                      </span>
                    </motion.div>
                  ))
                )}
                {/* Typing Indicator */}
                {botTyping && (
                  <div className="flex items-center space-x-2 justify-start">
                    <FaRobot className="text-purple-500" size={18} />
                    <div className="bg-neutral-700 text-neutral-200 px-3 py-2 rounded-lg shadow-md">
                      <span className="animate-pulse">...</span>
                    </div>
                  </div>
                )}
              </div>

              {/* Input Box */}
              <div className="flex items-center p-3 bg-neutral-800 border-t border-neutral-700">
                <motion.input
                  type="text"
                  placeholder="Type a message..."
                  className="w-full px-4 py-2 rounded-full bg-neutral-900 text-white placeholder-neutral-500 outline-none transition-all focus:bg-neutral-700"
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={handleKeyDown}
                  whileFocus={{ scale: 1.02 }}
                  transition={{ duration: 0.2 }}
                />
                <motion.button
                  onClick={sendMessage}
                  className="ml-3 p-2 rounded-full bg-gradient-to-br from-purple-500 to-indigo-600 text-white hover:shadow-lg focus:outline-none"
                  whileHover={{ scale: 1.1, rotate: 5 }}
                  whileTap={{ scale: 0.9 }}
                  transition={{ duration: 0.2 }}
                >
                  <FiSend size={18} />
                </motion.button>
              </div>
            </motion.div>
          </Draggable>
        )}
      </AnimatePresence>
    </div>
  )
}

export default Chatbot

