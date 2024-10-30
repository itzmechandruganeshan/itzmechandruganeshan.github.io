import { useState } from "react";
import AboutPic from "../assets/about.jpg";
import { ABOUT_TEXT } from "../constants";
import { motion } from "framer-motion";
import Modal from "./Model";
import Resume from "./Resume";

const About = () => {
  const [isModalOpen, setModalOpen] = useState(false);

  const openModal = () => setModalOpen(true);
  const closeModal = () => setModalOpen(false);

  return (
    <div className="border-b border-neutral-900 pb-4">
      <h2 className="my-20 text-center text-4xl">
        About 
        <span className="text-neutral-500"> Me</span>
      </h2>
      <div className="flex flex-wrap">
        <motion.div 
          whileInView={{ opacity: 1, x: 0 }}
          initial={{ opacity: 0, x: -100 }}
          transition={{ duration: 0.5 }}
          className="w-full lg:w-1/2 lg:p-8"
        >
          <div className="flex items-center justify-center">
            <img className="rounded-3xl shadow-2xl shadow-violet-900" src={AboutPic} alt="About" />
          </div>
        </motion.div>
        
        <motion.div 
          whileInView={{ opacity: 1, x: 0 }}
          initial={{ opacity: 0, x: 100 }}
          transition={{ duration: 0.5 }}
          className="w-full lg:w-1/2"
        >
          <div className="flex flex-col items-center lg:items-start">
            <p className="my-2 max-w-xl py-6 font-light tracking-tighter text-justify">
              {ABOUT_TEXT}
            </p>    

            <div className="flex space-x-2">
              <a
                href="Chandru's Resume.pdf"
                download="Chandru's Resume.pdf"
                className="rounded bg-stone-900 px-2 py-1 text-md font-medium text-purple-800 hover:shadow-lg hover:shadow-violet-900"
              >
                Download My Resume
              </a>
              
              <button
                onClick={openModal}
                className="rounded bg-stone-900 px-2 py-1 text-md font-medium text-purple-800 hover:shadow-lg hover:shadow-violet-900"
              >
                View My Resume
              </button>
            </div>
          </div>
        </motion.div>
      </div>

      {/* Modal for displaying the Resume */}
      {isModalOpen && (
        <Modal onClose={closeModal}>
          <Resume />
        </Modal>
      )}
    </div>
  );
};

export default About;
