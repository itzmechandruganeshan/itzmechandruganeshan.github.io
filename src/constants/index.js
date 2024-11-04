import PyMLRS from "../assets/projects/pymlrs.png";
import Alzheimer from "../assets/projects/alzheimer.jpg";
import Diabetes from "../assets/projects/diabetes.jpg";
import Pathogen from "../assets/projects/pathogen.jpg";
import Emotion from "../assets/projects/emotion.jpg";
import Rextractor from "../assets/projects/rextractor.ico";

export const HERO_CONTENT = `I am a dedicated Generative AI Engineer with a focus on crafting intelligent, innovative applications. With 10 months of hands-on experience, I have developed expertise in Python, LangChain, and Agent-based systems for building sophisticated generative AI workflows. I am passionate about leveraging these technologies to create impactful solutions that drive user engagement and business growth, continuously enhancing my skills to stay at the forefront of AI advancements.`;

export const ABOUT_TEXT = `I'm a dedicated Generative AI Engineer with a passion for crafting intelligent and innovative applications. I specialize in Python, LangChain, and agent-based systems, focusing on building sophisticated generative AI workflows. Currently, I’m expanding my skill set by learning React and AWS to further enhance my technical capabilities.

I have a strong interest in LLM agents and chatbots, exploring ways to create impactful, user-centered solutions that drive engagement and support business growth. My journey is fueled by continuous learning and a commitment to staying at the forefront of AI advancements.`;

export const EXPERIENCES = [
  {
    year: "May 2024 - Present",
    role: "Generative AI Engineer",
    company: "ISPG Technologies Pvt Ltd",
    description: `I am developing a Context-Aware Chatbot utilizing LangChain to enhance user interactions with intelligent responses. Additionally, I have implemented semantic search capabilities paired with smart filtering techniques, leveraging Python, LLMs, and Hugging Face. This work aims to create a more efficient and engaging user experience through advanced natural language processing.`,
    technologies: ["Python","Langchain","Langgraph","React.js", "MongoDB","Neo4j"],
  },
  {
    year: "Jan 2024 - April 2024",
    role: "Data Scientist Intern (R&D)",
    company: "Microbiological Laboratory Pvt Ltd",
    description: `At Microbiological Laboratory Research and Services (I) Pvt Ltd in Coimbatore, I led the development of an AI-driven framework that utilizes machine learning algorithms to analyze rt-PCR run files, drastically reducing processing time. I also designed a software solution featuring an innovative file parsing algorithm to extract raw data and created a standalone web application for visualizing and interpreting rt-PCR data related to meningoencephalitis pathogens. Additionally, I established a feature repository using Google Sheets to streamline the organization of data derived from rt-PCR run files.`,
    technologies: ["Python", "Tensorflow","Streamlit"],
  }
];

export const EDUCATION = [
  {
    year: "2022 - 2024",
    role: "M.Sc.Data Analytics",
    company: "Bharathiar University, Coimbatore",
    description: `I graduated with a major in Computer Science and Engineering, specializing in Artificial Intelligence and Machine Learning. I completed my undergraduate studies with a CGPA of 8.5, showcasing my strong academic performance and commitment to academic excellence.`,
  },
  {
    year: "2019 - 2022",
    role: "B.Sc.Statistics",
    company: "Government Arts College, Coimbatore",
    description: `I graduated with a major in Computer Science and Engineering, specializing in Artificial Intelligence and Machine Learning. I completed my undergraduate studies with a CGPA of 8.5, showcasing my strong academic performance and commitment to academic excellence.`,
  }
]
export const PROJECTS = [
  {
    title: "PyMLRS (Open Source)",
    image: PyMLRS,
    duration: "April 2024 – May 2024",
    description:
      `PyMLRS is an open-source Python library designed for Data Extraction, Data Visualization, Feature Extraction, and Classification of pathogens causing meningoencephalitis. Implemented a novel file parsing algorithm for accurate raw data extraction from High-Resolution Melt (HRM) and Amplification Curves in .rex files. Extracts features such as Peak Temperature, Width, Peak Prominence, Take-Off-Point, Take-Down-Point, Area Under the Curve of HRM, and Cycle Threshold from rt-PCR run files.`,
    technologies: ["Python", "Data Visualization", "Feature Engineering","Data Extraction","API Designing","File Parsing","Bioinformatics","Classification"],
    link:"https://pypi.org/project/PyMLRS/"
  },
  {
    title: "Rextractor (Open Source)",
    image: Rextractor,
    duration: "Current",
    description:
      `Rextractor is a specialized data extraction tool designed to enable independent data retrieval from Rotor-Gene PCR cyclers without relying on Rotor Gene Q-Rex software. Developed a unique algorithm for extracting HRM and Amplification data directly from .rex files, converting them efficiently into .xlsx format. Rextractor allows for rapid conversion of .rex files, processing hundreds in under a minute, compared to manual conversion methods that take over one minute per file.`,
    technologies: ["Python", "Data Extraction", "PCR Data Analysis","File Parsing","Rotor Gene Q-Rex"],
    link: "https://github.com/PyPCR/REXTRACTOR"
  },  
  {
    title: "Machine Learning for Alzheimer's Severity Prediction",
    image: Alzheimer,
    duration: "June 2023",
    description:
      `Developed a convolutional neural network model in TensorFlow for classifying Alzheimer's severity based on MRI brain images, achieving 96% accuracy. Tackled imbalanced data challenges using data augmentation techniques, and launched a user-accessible web application using Python and Streamlit.`,
    technologies: ["Python", "TensorFlow", "Keras","Alzheimer", "CNN", "Data Augmentation", "Streamlit"],
    link:"https://github.com/itzmechandruganeshan/Alzheimer-detection",
  },
  {
    title: "Predictive Modeling for Diabetic Outcome Classification",
    image: Diabetes,
    duration: "May 2023",
    description:
      `Utilized diabetes data from the Kaggle repository to train a decision tree model with 90% accuracy, incorporating feature engineering and meticulous data preprocessing. Conducted Exploratory Data Analysis (EDA) with statistical tests and visualizations to select key features. Built an interactive web application using Python and Streamlit for user engagement with visualizations.`,
    technologies: ["Python","Diabetes", "Decision Tree", "Feature Engineering", "EDA", "Streamlit"],
    link:"https://github.com/itzmechandruganeshan/Diabetes-Prediction"
  },
  {
    title: "AI Framework for Pathogen Classification",
    image: Pathogen,
    duration: "Jan 2024 – April 2024",
    description:
      `Developed an AI-based framework for classifying meningoencephalitis pathogens using HRM and CT data from rt-PCR analysis, achieving 97% accuracy. Leveraged a file-parsing technique for raw data extraction and a rule-based approach for genuine peak selection to reduce noise in the data.`,
    technologies: ["Python", "Machine Learning", "File Parsing", "rt-PCR Analysis","Peak Selection","Classification",],
    link:"https://github.com/itzmechandruganeshan/Pathogen-detector"
  },
  {
    title: "Deep Learning Architecture for Video-based Emotion Recognition",
    image: Emotion,
    duration: "Jul 2023 – Dec 2024",
    description:
      `Designed a deep learning architecture using a CNN model with pre-existing Kaggle dataset, employing Haar-cascade for facial feature extraction. Utilized an LSTM model to predict future emotions based on video frames' sequential probability values, achieving an average accuracy of 65%.`,
    technologies: ["Python", "TensorFlow", "CNN", "LSTM", "Haar-cascade","Emotion Recognition",],
    link:"https://github.com/itzmechandruganeshan/Emotion_Prediction"
  },
];

export const CONTACT = {
  address: "Coimbatore, Tamil Nadu, India",
  phoneNo: "+91 9087535918",
  email: "chandruganeshan24@gmail.com",
};
