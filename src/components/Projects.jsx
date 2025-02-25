import { PROJECTS } from "../constants";
import { motion } from "framer-motion";

const Projects = () => {
  return (
    <div className="border-b border-neutral-900 pb-4">
      <motion.h2
        whileInView={{ opacity: 1, y: 0 }}
        initial={{ opacity: 0, y: -100 }}
        transition={{ duration: 0.8 }}
        className="my-20 text-center text-4xl"
      >
        Projects
      </motion.h2>
      <div>
        {PROJECTS.map((project, index) => (
          <div key={index} className="mb-8 flex flex-wrap lg:justify-center">
            <motion.div
              whileInView={{ opacity: 1, x: 0 }}
              initial={{ opacity: 0, x: -100 }}
              transition={{ duration: 1 }}
              className="w-full lg:w-1/4"
            >
              <img
                src={project.image}
                width={150}
                height={150}
                alt={project.title}
                className="mb-6 rounded"
              />
            </motion.div>
            <motion.div
              whileInView={{ opacity: 1, x: 0 }}
              initial={{ opacity: 0, x: 100 }}
              transition={{ duration: 1 }}
              className="w-full max-w-xl lg:w-3/4"
            >
              <div className="flex items-center justify-between">
                <h6 className="mb-2 font-semibold">{project.title}</h6>
                <a
                  href={project.link}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="mr-2 mt-4 rounded bg-neutral-900 px-2 py-1
                                text-sm font-medium text-purple-800 hover:shadow-lg hover:shadow-violet-900"
                >
                  View
                </a>
              </div>
              <p className="mb-4 text-neutral-400 text-justify">{project.description}</p>
              <p className="flex flex-wrap gap-y-2">
                {project.technologies.map((tech, index) => (
                  <span
                    key={index}
                    className="mr-1 mt-1 rounded bg-neutral-900 px-2 py-1
                                text-sm font-medium text-purple-800 hover:shadow-lg hover:shadow-violet-900"
                  >
                    {tech}
                  </span>
                ))}
              </p>
            </motion.div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default Projects;
