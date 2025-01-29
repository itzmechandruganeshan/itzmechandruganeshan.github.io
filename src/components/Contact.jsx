import { CONTACT } from "../constants";
import { motion } from "framer-motion";
import { FaGithub, FaLinkedin, FaEnvelope } from "react-icons/fa";

const Contact = () => {
  return (
    <div className="border-b border-neutral-900 pb-20">
      <motion.h2 
        whileInView={{ opacity: 1, y: 0 }} 
        initial={{ opacity: 0, y: -100 }} 
        transition={{ duration: 0.5 }} 
        className="my-10 text-center text-4xl"
      >
        Get in Touch
      </motion.h2>
      
      <div className="text-center tracking-tighter">
        <motion.p
          whileInView={{ opacity: 1, x: 0 }} 
          initial={{ opacity: 0, x: -100 }} 
          transition={{ duration: 0.5 }}
          className="my-4 text-neutral-400"
        >
          {CONTACT.address}
        </motion.p>
        
        <motion.p
          whileInView={{ opacity: 1, x: 0 }} 
          initial={{ opacity: 0, x: -100 }} 
          transition={{ duration: 0.5 }}
          className="my-4 text-neutral-400"
        >
          {CONTACT.phoneNo}
        </motion.p>
    
        {/* Social Icons Section */}
        <div className="flex justify-center space-x-6 mt-8">
          <motion.a 
            whileHover={{ scale: 1.1 }} 
            whileTap={{ scale: 0.9 }}
            href="https://github.com/itzmechandruganeshan" 
            target="_blank" 
            rel="noopener noreferrer"
            className="text-neutral-400 hover:text-purple-900 transition duration-200"
          >
            <FaGithub size={30} />
          </motion.a>
          
          <motion.a 
            whileHover={{ scale: 1.1 }} 
            whileTap={{ scale: 0.9 }}
            href="https://linkedin.com/in/chandru-g24" 
            target="_blank" 
            rel="noopener noreferrer"
            className="text-neutral-400 hover:text-purple-900 transition duration-200"
          >
            <FaLinkedin size={30} />
          </motion.a>
          
          <motion.a 
            whileHover={{ scale: 1.1 }} 
            whileTap={{ scale: 0.9 }}
            href={`mailto:${CONTACT.email}`}
            className="text-neutral-400 hover:text-purple-900 transition duration-200"
          >
            <FaEnvelope size={30} />
          </motion.a>
        </div>
      </div>
    </div>
  );
};

export default Contact;
