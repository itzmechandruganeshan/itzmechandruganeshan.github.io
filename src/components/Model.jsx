// components/Modal.js
import { motion } from "framer-motion";
import PropTypes from "prop-types";

const Modal = ({ onClose, children }) => {
  return (
    <motion.div 
      className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
    >
      <motion.div 
        className="relative w-full max-w-5xl max-h-[90vh] p-6 bg-white rounded-lg shadow-lg"
        initial={{ scale: 0.8 }}
        animate={{ scale: 1 }}
        exit={{ scale: 0.8 }}
        transition={{ duration: 0.3 }}
      >
        {/* Close button */}
        <button
          onClick={onClose}
          className="absolute top-1 right-1 text-black text-xl hover:scale-lg transition"
        >
          ✕
        </button>

        {/* Modal content with hidden scrollbar */}
        <div className="max-h-[80vh] overflow-y-scroll scrollbar-hidden">
          {children}
        </div>
      </motion.div>
    </motion.div>
  );
};

// Define prop types for validation
Modal.propTypes = {
    onClose: PropTypes.func.isRequired,
    children: PropTypes.node.isRequired,
};

export default Modal;
