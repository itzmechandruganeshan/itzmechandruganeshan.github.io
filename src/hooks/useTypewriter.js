import { useState, useEffect } from 'react';

const useTypewriter = (texts, typingSpeed = 100, delay = 2000) => {
  const [displayText, setDisplayText] = useState('');
  const [isDeleting, setIsDeleting] = useState(false);
  const [textIndex, setTextIndex] = useState(0);

  useEffect(() => {
    let typingTimeout;

    // Typing effect logic
    if (!isDeleting && displayText === texts[textIndex]) {
      // Pause before deleting
      typingTimeout = setTimeout(() => setIsDeleting(true), delay);
    } else if (isDeleting && displayText === '') {
      // Move to the next word and start typing
      setIsDeleting(false);
      setTextIndex((prev) => (prev + 1) % texts.length); // Cycle to the next title
    } else {
      // Type or delete characters
      typingTimeout = setTimeout(() => {
        setDisplayText((prev) =>
          isDeleting ? texts[textIndex].slice(0, prev.length - 1) : texts[textIndex].slice(0, prev.length + 1)
        );
      }, isDeleting ? typingSpeed / 2 : typingSpeed);
    }

    return () => clearTimeout(typingTimeout);
  }, [displayText, isDeleting, textIndex, texts, delay, typingSpeed]);

  return displayText;
};

export default useTypewriter;
