import { motion } from 'framer-motion';

const BlogPyMLRS = () => {
  return (
    <div className="relative h-full w-full bg-transparent text-neutral-300 p-8">
      <motion.div
        className="relative z-10 max-w-6xl mx-auto"
        initial={{ opacity: 0, y: 50 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
      >
        <h1 className="text-4xl text-center mb-8 font-light tracking-tighter">AI-based framework for pathogen classification through rt-PCR data</h1>
        
        {/* Flex container for overview and video */}
        <div className="flex flex-col md:flex-row space-x-4">
          {/* Overview Content */}
          <motion.div
            className="flex-1 p-6 rounded-lg shadow-lg bg-transparent transition duration-300 font-light tracking-tighter"
          >
            <h2 className="text-2xl mb-4 font-light tracking-tighter">Have you heard abour rt-PCR analysis?</h2>
            <p className='w-full text-justify'>
                rt-PCR (reverse transcription polymerase chain reaction) analysis is a lab technique used to find and measure RNA in a sample. First, it converts RNA into DNA, and then it makes many copies of that DNA to make it easier to detect. This method is commonly used in medicine to test for viruses, like COVID-19, and to study how genes are expressed in different conditions. It’s a valuable tool for understanding biological processes and diagnosing diseases.
            </p>
          </motion.div>

          {/* YouTube Video Embed */}
          <motion.div
            className="flex-1 p-6 rounded-lg shadow-lg bg-transparent transition duration-300 font-light tracking-tighter"
          >
            {/* <h2 className="text-2xl mb-4 font-light tracking-tighter">Watch Our Overview Video</h2> */}
            <iframe width="500" height="315" src="https://www.youtube.com/embed/xiTQ6-MOgdk?si=ZIcNJ2rejU70cxWw" title="YouTube video player" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" allowfullscreen></iframe>
          </motion.div>
        </div>

        <section className="space-y-6 mt-8">
          {/* Remaining content sections */}
          <motion.div className="p-6 rounded-lg shadow-lg bg-transparent transition duration-300 font-light tracking-tighter">
            <h2 className="text-2xl mb-4 font-light tracking-tighter">Challenges in Traditional Analysis</h2>
            <p>
              Conventional HRMA workflows depend heavily on expert manual analysis, often prone to interpretation errors and time-consuming
              due to the high complexity of genetic data. Mid to large-sized labs face additional hurdles with vendor-dependent software
              and inconsistent analytical tools.
            </p>
          </motion.div>

          <motion.div className="p-6 rounded-lg shadow-lg bg-transparent transition duration-300 font-light tracking-tighter">
            <h2 className="text-2xl mb-4 font-light tracking-tighter">Features and Innovations of PyMLRS</h2>
            <p>
              PyMLRS is engineered to tackle these challenges with a Python-based framework that integrates high-precision algorithms
              and data processing methods. Some core features include automated data acquisition, pre-processing for clean, structured
              analysis, and customized AI-driven predictive models for accurate diagnostics.
            </p>
          </motion.div>

          <motion.div className="p-6 rounded-lg shadow-lg bg-transparent transition duration-300 font-light tracking-tighter">
            <h2 className="text-2xl mb-4 font-light tracking-tighter">Data Processing Pipeline</h2>
            <p>
              The PyMLRS pipeline uses raw fluorescence data from PCR devices, followed by smooth filtering via Savitzky-Golay
              algorithms, and logical thresholding to identify DNA melt peaks. Each step is optimized to enhance analysis quality
              and reliability, streamlining processes for high-throughput labs.
            </p>
          </motion.div>

          <motion.div className="p-6 rounded-lg shadow-lg bg-transparent transition duration-300 font-light tracking-tighter">
            <h2 className="text-2xl mb-4 font-light tracking-tighter">Conclusion</h2>
            <p>
              With PyMLRS, laboratories can now perform HRMA and PCR diagnostics with a new level of precision and speed, minimizing
              the manual workload and boosting confidence in test results. By bridging AI and laboratory needs, PyMLRS is set to
              become an invaluable asset for laboratories around the world.
            </p>
          </motion.div>
        </section>
      </motion.div>
    </div>
  );
};

export default BlogPyMLRS;