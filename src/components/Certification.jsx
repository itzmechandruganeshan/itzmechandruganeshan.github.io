import Draggable from "react-draggable";
import { motion, AnimatePresence } from "framer-motion";
import { BiMessageSquareDetail } from "react-icons/bi";
import { FaRobot } from "react-icons/fa";
import { IoClose } from "react-icons/io5";
import { useState } from "react";
import { FiSend } from "react-icons/fi";
import { BsFillPersonFill } from "react-icons/bs";

const Chatbot = () => {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");

  const toggleChatbot = () => setIsOpen(!isOpen);

  const sendMessage = () => {
    if (input.trim()) {
      const newMessages = [...messages, { text: input, sender: "user" }];
      setMessages(newMessages);
      setInput("");

      // Simulate bot response
      setTimeout(() => {
        setMessages((prevMessages) => [
          ...prevMessages,
          { text: "Hello! How can I assist you?", sender: "bot" },
        ]);
      }, 1000);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter") {
      sendMessage();
    }
  };

  return (
    <div>
      {/* Chat Message Icon */}
      <motion.div
        className="fixed bottom-10 right-10 p-4 bg-gradient-to-r from-purple-700 to-purple-900 rounded-full cursor-pointer shadow-lg"
        whileHover={{ scale: 1.1 }}
        onClick={toggleChatbot}
      >
        <BiMessageSquareDetail color="white" size={28} />
      </motion.div>

      {/* Chatbot Window */}
      <AnimatePresence>
        {isOpen && (
          <Draggable handle=".chatbot-header">
            <motion.div
              className="fixed bottom-20 right-10 w-80 sm:w-96 bg-neutral-900 rounded-2xl shadow-2xl overflow-hidden"
              initial={{ opacity: 0, y: 50 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: 50 }}
              transition={{ duration: 0.3, ease: "easeInOut" }}
            >
              {/* Header */}
              <div className="flex items-center justify-between px-4 py-3 bg-gradient-to-r from-purple-800 to-purple-600 text-white rounded-t-2xl chatbot-header cursor-move">
                <h3 className="text-lg font-semibold">Virtual Chandru</h3>
                <IoClose
                  size={24}
                  className="cursor-pointer hover:text-red-500 transition duration-200"
                  onClick={toggleChatbot}
                />
              </div>

              {/* Chat Content */}
              <div className="p-4 h-80 overflow-y-auto text-sm text-neutral-300 space-y-3">
                {messages.length === 0 ? (
                  <p className="text-center text-neutral-500">Ask me anything!</p>
                ) : (
                  messages.map((message, index) => (
                    <motion.div
                      key={index}
                      initial={{ opacity: 0, x: message.sender === "user" ? 30 : -30 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ duration: 0.2 }}
                      className={`flex items-center space-x-2 ${
                        message.sender === "user" ? "justify-end" : "justify-start"
                      }`}
                    >
                      {message.sender === "bot" ? (
                        <FaRobot className="text-purple-500" size={20} />
                      ) : (
                        <BsFillPersonFill className="text-blue-500" size={20} />
                      )}
                      <div
                        className={`px-4 py-2 rounded-xl ${
                          message.sender === "user"
                            ? "bg-blue-600 text-white"
                            : "bg-neutral-800 text-neutral-200"
                        } shadow-md`}
                      >
                        {message.text}
                      </div>
                    </motion.div>
                  ))
                )}
              </div>

              {/* Input Box */}
              <div className="flex items-center p-3 bg-neutral-800 border-t border-neutral-700">
                <input
                  type="text"
                  placeholder="Type a message..."
                  className="w-full px-3 py-2 rounded-lg bg-neutral-900 text-white placeholder-neutral-500 outline-none transition-all focus:bg-neutral-700"
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={handleKeyDown}
                />
                <button
                  onClick={sendMessage}
                  className="ml-2 p-2 rounded-full bg-purple-600 text-white hover:bg-purple-700 focus:outline-none transition-transform transform hover:scale-110"
                >
                  <FiSend size={18} />
                </button>
              </div>
            </motion.div>
          </Draggable>
        )}
      </AnimatePresence>
    </div>
  );
};

export default Chatbot;
