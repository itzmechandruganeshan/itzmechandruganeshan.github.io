    import PropTypes from "prop-types";

    const Resume = () => {
        return (
            <div className="my-10 p-8 lg:px-16 md:px-12 sm:px-6 bg-white bg-transparent text-gray-900 rounded-xl shadow-2xl max-w-5xl mx-auto">
                {/* Header */}
                <h1 className="text-4xl font-bold text-center text-gray-800 mb-4">Chandru Ganeshan</h1>
                <p className="text-center text-lg text-gray-600 mb-2">Machine Learning Engineer</p>
                <p className="text-center text-gray-500 mb-2">
                    Contact: (+91) - 9087535918 | Email: <a href="mailto:chandruganeshan24@gmail.com" className="underline hover:text-cyan-500 transition duration-300">chandruganeshan24@gmail.com</a>
                </p>
                <p className="text-center text-gray-500 mb-6">
                    GitHub: <a href="https://github.com/itzmechandruganeshan" className="text-cyan-600 hover:underline hover:text-cyan-500 transition duration-300">Github/itzmechandruganeshan</a> | 
                    LinkedIn: <a href="https://linkedin.com/in/chandru-g24" className="text-cyan-600 hover:underline hover:text-cyan-500 transition duration-300">LinkedIn/chandru-g24</a>
                </p>

                {/* Education Section */}
                <Section title="Education">
                    <ul className="list-disc list-inside mb-4 text-gray-700 space-y-4">
                        <li className="bg-white p-4 rounded-xl shadow-lg border-2 border-transparent hover:border-gradient-to-r hover:from-cyan-400 hover:to-purple-400 transition-all duration-300">
                            <strong>Bharathiar University, Coimbatore, India</strong><br />
                            Master of Science – Data Analytics; CGPA: 8.16<br />
                            Graduation: Oct 2024
                        </li>
                        <li className="bg-white p-4 rounded-xl shadow-lg border-2 border-transparent hover:border-gradient-to-r hover:from-pink-400 hover:to-purple-400 transition-all duration-300">
                            <strong>Government Arts College, Coimbatore, India</strong><br />
                            Bachelor of Science – Statistics; CGPA: 7.93<br />
                            Graduation Date: July 2022
                        </li>
                    </ul>
                </Section>

                {/* Skills Section */}
                <Section title="Skills">
                    <ul className="list-disc list-inside mb-4 text-gray-700 space-y-3">
                        <li><strong>Programming Languages:</strong> Python, R (dplyr, ggplot, plotly)</li>
                        <li><strong>Databases:</strong> MySQL, PostgresSQL, Neo4j</li>
                        <li><strong>Libraries:</strong> Python (langchain, langgraph, autogen, crewai, huggingface, tensorflow, keras, 
                            open-cv, sklearn, streamlit, pandas, numpy, scipy, matplotlib, seaborn, plotly)</li>
                        <li><strong>Data wrangling:</strong> Data extraction, Data cleaning, Exploratory Data Analysis, Feature Engineering
                        and selection.</li>
                        <li><strong>Machine Learning:</strong> Data modelling, Clustering and Classification, Regression analysis, Predictive 
modelling, Model validation, Fine tuning, Deployment, CNN, RCNN, LSTM, 
Transformer models</li>
                        <li><strong>Generative AI Frameworks:</strong> Langchain, Langgraph, Autogen, CrewAI, Huggingface, Dialogflow CX</li>
                        <li><strong>DevOps:</strong> Git, Github, Docker, Postman, Flask, FastAPI</li>
                    </ul>
                </Section>

                {/* Work Experience Section */}
                <Section title="Work Experience">
                    <ul className="list-disc list-inside mb-4 text-gray-700 space-y-3">
                        <li className="bg-white p-4 rounded-xl shadow-lg border-2 border-transparent hover:border-gradient-to-r hover:from-green-400 hover:to-blue-400 transition-all duration-300">
                            <strong>Machine Learning Engineer</strong> | CloudSide Technologies Pvt Ltd, Coimbatore<br />
                            Jan 2025 – Present
                            <ul className="list-decimal list-inside mt-2 space-y-1">
                                <li>Building a Chatbot using Dialogflow CX.</li>
                            </ul>
                        </li>
                        <li className="bg-white p-4 rounded-xl shadow-lg border-2 border-transparent hover:border-gradient-to-r hover:from-green-400 hover:to-blue-400 transition-all duration-300">
                            <strong>Generative AI Engineer</strong> | ISPG Technologies Pvt Ltd, Kochi<br />
                            May 2024 – Dec 2024
                            <ul className="list-decimal list-inside mt-2 space-y-1">
                                <li>Building a chatbot using LangChain to provide intelligent, contextually relevant responses for enhanced user interactions.</li>
                                <li>Implementing semantic search to improve the chatbot’s ability to understand and retrieve relevant information effectively.</li>
                                <li>Utilizing advanced filtering mechanisms in combination with LLMs and Hugging Face tools to deliver accurate, focused responses.</li>
                                <li>Aiming to create an engaging and efficient user experience through sophisticated NLP and language model-driven processing.</li>
                            </ul>
                        </li>
                        <li className="bg-white p-4 rounded-xl shadow-lg border-2 border-transparent hover:border-gradient-to-r hover:from-green-400 hover:to-blue-400 transition-all duration-300">
                            <strong>Data Scientist (Intern)</strong> | Microbiological Laboratory Research and Services (I) Pvt Ltd, Coimbatore<br />
                            January 2024 – April 2024
                            <ul className="list-decimal list-inside mt-2 space-y-1">
                                <li>Spearheaded the creation of an AI-driven framework to analyze rt-PCR run files.</li>
                                <li>Created a feature repository using Google Sheets to streamline feature organization.</li>
                                <li>Developed a file parsing algorithm to extract data from rt-PCR run files.</li>
                                <li>Designed a web application for data extraction, visualization, and interpretation of meningoencephalitis pathogens.</li>
                            </ul>
                        </li>
                    </ul>
                </Section>

                {/* Self Projects Section */}
                <Section title="Self Projects">
                    <ul className="list-disc list-inside mb-4 text-gray-700 space-y-3">
                        <li className="bg-white p-4 rounded-xl shadow-lg border-2 border-transparent hover:border-gradient-to-r hover:from-orange-400 hover:to-red-400 transition-all duration-300">
                            <a href="https://github.com/itzmechandruganeshan/PyMLRS" target="_blank" rel="noopener noreferrer" className="hover:underline hover:text-cyan-500 transition duration-300"><strong>PyMLRS (Open Source)</strong><br /></a>
                            April 2024 – May 2024
                            <ul className="list-decimal list-inside mt-2 space-y-1">
                                <li>PyMLRS is an open-source Python library designed for robust Data Extraction, Data Visualization, efficient Feature Extraction, and Accurate Classification of pathogens causing meningoencephalitis.</li>
                                <li>Implemented novel file parsing algorithm for accurate raw data extraction of High Resolution Melt and Amplification Curve from .rex files.</li>
                                <li>Extracts features such as Peak Temperature, Width, Peak Prominence, Take-Off-Point, Take-Down-Point, and Area Under the Curve of HRM and Cycle Threshold of Amplification Curve from rt-PCR run files.</li>
                            </ul>
                        </li>
                        <li className="bg-white p-4 rounded-xl shadow-lg border-2 border-transparent hover:border-gradient-to-r hover:from-blue-400 hover:to-purple-400 transition-all duration-300">
                        <a href="https://github.com/itzmechandruganeshan/Alzheimer-detection" target="_blank" rel="noopener noreferrer" className="hover:underline hover:text-cyan-500 transition duration-300"><strong>Machine Learning-based Alzheimer’s Severity Prediction</strong><br /></a>
                            June 2023
                            <ul className="list-decimal list-inside mt-2 space-y-1">
                                <li> Utilized pre-existing MRI scanned brain images to train a convolutional neural network in TensorFlow, maximizing efficiency and accuracy</li>
                                <li>Implemented data augmentation techniques to tackle imbalanced data challenges, employing a range of augmentation methods to enhance dataset diversity</li>
                                <li>Achieved 96% accuracy in classifying Alzheimer severity by developing a CNN model tailored for the task.</li>
                                <li>Launched a web application with Python and Streamlit, now accessible on the community cloud for seamless user interaction.</li>
                            </ul>
                        </li>
                        <li className="bg-white p-4 rounded-xl shadow-lg border-2 border-transparent hover:border-gradient-to-r hover:from-blue-400 hover:to-purple-400 transition-all duration-300">
                        <a href="https://github.com/itzmechandruganeshan/Diabetes-Prediction" target="_blank" rel="noopener noreferrer" className="hover:underline hover:text-cyan-500 transition duration-300"><strong>Predictive modeling for diabetic outcome classification: A Machine Learning Framework</strong><br /></a>
                            <ul className="list-decimal list-inside mt-2 space-y-1">
                                <li> Leveraged diabetes data from the Kaggle repository to train a decision tree model, enhancing its performance through meticulous data preprocessing and feature engineering.</li>
                                <li>Conducted Exploratory Data Analysis (EDA) employing statistical tests and visualizations, meticulously selecting pertinent features to train the model.</li>
                                <li>Achieved a 90% accuracy rate in predicting diabetic patient outcomes by developing a Decision Tree model leveraging vital parameters.</li>
                                <li>Implemented a dynamic web application using Python and Streamlit, featuring an interactive dashboard with engaging visualizations.</li>
                            </ul>
                        </li>
                    </ul>
                </Section>

                {/* Academic Projects Section */}
                <Section title="Academic Projects">
                    <ul className="list-disc list-inside mb-4 text-gray-700 space-y-3">
                        <li className="bg-white p-4 rounded-xl shadow-lg border-2 border-transparent hover:border-gradient-to-r hover:from-teal-400 hover:to-indigo-400 transition-all duration-300">
                            <strong>M.Sc. Thesis: AI Framework for Pathogen Classification via RT-PCR</strong><br />
                            January 2024 – April 2024
                            <ul className="list-decimal list-inside mt-2 space-y-1">
                                <li>Developed framework for classifying meningoencephalitis pathogens with HRM and CT extracted from rt-PCT data.</li>
                                <li>Executed data acquisition through File-parsing technique, to extract raw data from rt-PCR data.</li>
                                <li>Maintain genuine peaks through a rule-based approach, effectively removing noise from rt-PCR data signal peaks.</li>
                                <li>Generated synthetic features to overcome the issue of lack of positive data by inspecting original features of rt-PCR data.</li>
                                <li>Developed ML model to classify the Meningoencephalitis pathogens with 97% accuracy, aligning with original lab reports.</li>
                            </ul>
                        </li>
                        <li className="bg-white p-4 rounded-xl shadow-lg border-2 border-transparent hover:border-gradient-to-r hover:from-pink-500 hover:to-purple-500 transition-all duration-300">
                            <strong>M.Sc. Mini Project: Deep Learning for Video-Based Emotion Recognition</strong><br />
                            July 2023 – December 2024
                            <ul className="list-decimal list-inside mt-2 space-y-1">
                                <li>Utilized pre-existing dataset of from Kaggle to train convolutional neural network model in Tensorflow, duet to lack of emotions data.</li>
                                <li>Addressed real-time image challenges using the Haar-cascade algorithm for extracting facial features.</li>
                                <li>Stored probability values of each video frame to train the LSTM model, achieving an average accuracy of 65%.</li>
                            </ul>
                        </li>
                    </ul>
                </Section>

                {/* Activities Section */}
                <Section title="Activities">
                    <p className="text-gray-700 mb-4">
                        Delivered a detailed workshop explaining the math behind machine learning algorithms. Partnered with the Department of Computer Applications to host an interactive session, involving 60 students in the learning experience.
                    </p>
                </Section>

                {/* Released Software Section */}
                <Section title="Released Software">
                    <ul className="list-disc list-inside mb-4 text-gray-700 space-y-3">
                        <li className="bg-white p-4 rounded-xl shadow-lg border-2 border-transparent hover:border-gradient-to-r hover:from-yellow-500 hover:to-orange-500 transition-all duration-300">
                            <a href="https://github.com/itzmechandruganeshan/REXTRACTOR" target="_blank" rel="noopener noreferrer" className="hover:underline hover:text-cyan-500 transition duration-300"><strong>Rextractor</strong></a>
                            <ul className="list-decimal list-inside mt-2 space-y-1 ml-4">
                                <li>Customized tool for independent PCR data extraction from .rex files, eliminating reliance on Rotor-Gene Q-Rex software.</li>
                                <li>Capable of extracting HRM and Amplification data from Rotor-Gene Q-Rex .rex files, offering a standalone solution for conversion to Excel format.</li>
                                <li>Significantly reduces processing time, converting files in less than a second per file compared to manual methods taking over a minute.</li>
                            </ul>
                        </li>
                    </ul>
                </Section>

                {/* Certifications Section */}
                <Section title="Certifications">
                    <ul className="list-disc list-inside mb-4 text-gray-700 space-y-3">
                        {[  { name: "LangGraph- Develop LLM powered AI agents with LangGraph", url:"https://www.udemy.com/certificate/UC-00e13ebc-29cd-4420-9dc8-90254c1ecf86/"},
                            { name: 'Graph Academy – Neo4j Fundamentals', url: 'https://graphacademy.neo4j.com/c/c384de60-e4cb-4cef-a6a3-0d4656b4b1d1/' },
                            { name: 'Graph Academy – Cypher Fundamentals', url: 'https://graphacademy.neo4j.com/c/921a29f6-edf5-46a3-a29d-a3226a1a5a97/' },
                            { name: 'NPTEL – Descriptive Statistics with R', url: 'https://archive.nptel.ac.in/noc/B2C/candidate_login/candidate_scores.php?courseid=noc22-mg87' },
                            
                        ].map(cert => (
                            <li key={cert.name} className="bg-white p-2 rounded-xl shadow-lg border-2 border-transparent hover:border-gradient-to-r hover:from-cyan-500 hover:to-blue-500 transition-all duration-300">
                                <a href={cert.url} target="_blank" rel="noopener noreferrer" className="hover:underline hover:text-cyan-500 transition duration-300">
                                    {cert.name}
                                </a>
                            </li>
                        ))}
                    </ul>
                </Section>

            </div>
        );
    };

    const Section = ({ title, children }) => (
        <div className="mb-10">
            <h2 className="text-2xl font-semibold mb-4 text-gray-800 border-b border-gray-300 pb-2 transition duration-300 ease-in-out hover:text-gray-600">
                {title}
            </h2>
            {children}
        </div>
    );

    // Define prop types for validation
    Section.propTypes = {
        title: PropTypes.func.isRequired,
        children: PropTypes.node.isRequired,
    };

    export default Resume;
