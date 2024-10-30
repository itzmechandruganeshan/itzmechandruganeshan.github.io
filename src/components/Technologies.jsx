import { motion } from "framer-motion";

// Animation variant for the icons
const iconVariants = (duration) => ({
    initial: { y: -10 },
    animate: {
        y: [20, -20],
        transition: {
            duration: duration,
            ease: "linear",
            repeat: Infinity,
            repeatType: "reverse",
        },
    },
});

// Define categories with images and animation duration
const categories = [
        // New section for Programming Languages
    {
        title: "Programming Languages",
        icons: [
            { src: "/images/python.svg", alt: "Python", duration: 3 },
            { src: "/images/r.svg", alt: "R", duration: 3 }
        ],
    },
    {
        title: "Databases",
        icons: [
            { src: "/images/msql.svg", alt: "MySQL", duration: 5 },
            { src: "/images/neo4j.svg", alt: "Neo4j", duration: 5 },
            { src: "/images/postgresql.svg", alt: "PostgreSQL", duration: 5 }
        ],
    },
    {
        title: "Machine Learning & Computer Vision",
        icons: [
            { src: "/images/tensorflow.svg", alt: "TensorFlow", duration: 4 },
            { src: "/images/scikit-learn.svg", alt: "Scikit-Learn", duration: 4 },
            { src: "/images/opencv.svg", alt: "OpenCV", duration: 6 },
            { src: "/images/keras.svg", alt: "Keras", duration: 6 },
            { src: "/images/streamlit.svg", alt: "Streamlit", duration: 3 },
        ],
    },
    {
        title: "Data Analytics",
        icons: [
            { src: "/images/excel.svg", alt: "Excel", duration: 2.5 },
            { src: "/images/powerbi.svg", alt: "Power BI", duration: 2.5 },
            { src: "/images/pandas.svg", alt: "Pandas", duration: 2.5 },
            { src: "/images/numpy.svg", alt: "NumPy", duration: 2.5 },
            { src: "/images/matplotlib.svg", alt: "Matplotlib", duration: 2.5 },
            { src: "/images/searborn.svg", alt: "Seaborn", duration: 2.5 },
            { src: "/images/plotly.svg", alt: "Plotly", duration: 2.5 },
            { src: "/images/scipy.svg", alt: "Scipy", duration: 2.5 },
        ],
    },
    {
        title: "DevOps",
        icons: [
            { src: "/images/fastapi.svg", alt: "FastAPI", duration: 3 },
            { src: "/images/docker.svg", alt: "Docker", duration: 3 },
            { src: "/images/postman.svg", alt: "Postman", duration: 3 },
            { src: "/images/vscode.svg", alt: "VS Code", duration: 3 },
            { src: "/images/pycharm.svg", alt: "VS Code", duration: 3 },
            { src: "/images/flask.png", alt: "Flask", duration: 3 },
        ],
    },
    {
        title: "Generative AI",
        icons: [
            { src: "/images/langchain.svg", alt: "LangChain", duration: 3 },
            { src: "/images/langgraph.svg", alt: "Langgraph", duration: 3 },
            { src: "/images/huggingface.svg", alt: "Hugging Face", duration: 2 },
            { src: "/images/autogen.svg", alt: "Autogen", duration: 3 },
            { src: "/images/crewai.svg", alt: "Crewa AI", duration: 3 }
        ],
    },
    {
        title: "Learning",
        icons: [
            { src: "/images/react.svg", alt: "React", duration: 3 },
            { src: "/images/js.svg", alt: "JavaScript", duration: 3 }
        ],
    },

];

const Technologies = () => {
    return (
        <div className="border-b border-neutral-800 pb-24">
            <motion.h1
                whileInView={{ opacity: 1, y: 0 }}
                initial={{ opacity: 0, y: -100 }}
                transition={{ duration: 1.5 }}
                className="my-20 text-center text-4xl">
                Technologies I work with
            </motion.h1>

            <div className="flex flex-wrap justify-center gap-10">
                {/* Render each category */}
                {categories.map((category, catIndex) => (
                    <div key={catIndex} className="flex flex-col items-center">
                        <motion.h2
                            whileInView={{ opacity: 1, x: 0 }}
                            initial={{ opacity: 0, x: -100 }}
                            transition={{ duration: 1.5 }}
                            className="text-2xl text-center mb-4">
                            {category.title}
                        </motion.h2>

                        <motion.div
                            whileInView={{ opacity: 1, x: 0 }}
                            initial={{ opacity: 0, x: -100 }}
                            transition={{ duration: 1.5 }}
                            className="flex flex-wrap items-center justify-center gap-4">
                            {/* Render each icon as an image */}
                            {category.icons.map((icon, index) => (
                                <motion.div
                                    key={index}
                                    variants={iconVariants(icon.duration)}
                                    initial="initial"
                                    animate="animate"
                                    className="flex items-center justify-center w-36 h-36 border-4 border-neutral-800 bg-transparent bg-neutral-900 rounded-full transition-transform duration-300 hover:scale-105 hover:shadow-lg hover:shadow-violet-900 perspective-1000">
                                    <motion.img
                                        src={icon.src}
                                        alt={icon.alt}
                                        className="w-24 h-24 object-contain"
                                        whileHover={{ rotateY: 180 }}
                                    />
                                </motion.div>
                            ))}
                        </motion.div>
                    </div>
                ))}
            </div>
        </div>
    );
};

export default Technologies;
