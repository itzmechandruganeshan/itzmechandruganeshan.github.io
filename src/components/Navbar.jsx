import logo from '../assets/chandrulogo.png'
import { FaLinkedin } from 'react-icons/fa';
import { FaGithub } from 'react-icons/fa';
import { IoMdMail } from "react-icons/io";
import { motion } from "framer-motion";

const Navbar = () => {
  return <nav className="mb-20 flex items-center justify-between py-6">
    <div className="flex flex-shrink-0 items-center">
        <img className= "mx-2 w-12" src={logo} alt="Chandru Ganeshan Logo"></img>
    </div>
    <div className="m-8 flex items-center justify-center gap-4 text-2xl">
      <motion.a whileHover={{ scale: 1.5 }} whileTap={{ scale: 1.5 }} href="https://www.linkedin.com/in/chandru-g24" target="_blank" rel="noopener noreferrer">
        <FaLinkedin cursor={"pointer"} className='"text-neutral-400 hover:text-purple-900 transition duration-200'/>
      </motion.a>
      <motion.a whileHover={{ scale: 1.5 }} whileTap={{ scale: 1.5 }} href="https://github.com/itzmechandruganeshan" target="_blank" rel="noopener noreferrer">
        <FaGithub cursor={"pointer"} className='"text-neutral-400 hover:text-purple-900 transition duration-200'/>
      </motion.a>
      <motion.a whileHover={{ scale: 1.5 }} whileTap={{ scale: 1.5 }} href="mailto:chandruganeshan24@gmail.com" target="_blank" rel="noopener noreferrer">
        <IoMdMail cursor={"pointer"} className='"text-neutral-400 hover:text-purple-900 transition duration-200'/>
      </motion.a>
    </div>
    </nav>;
};

export default Navbar