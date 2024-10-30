import Navbar from "./components/Navbar";
import About from "./components/About";
import Hero from "./components/Hero";
import Technologies from "./components/Technologies";
import Experience from "./components/Experience";
import Projects from "./components/Projects";
import Contact from "./components/Contact";
import { Helmet } from "react-helmet";
import iconImage from "/Hero_image.png";
import Copyright from "./components/Copyright";

const App = () => {
  return (
    <div className="overflow-x-hidden text-neutral-300 antialiased selection:bg-cyan-300 selection:text-cyan-900">
      <Helmet>
        <title>CG Portfolio</title>
        <link rel="icon" type="image/png" href={iconImage} className="rounded-full w-16 h-16"/>
      </Helmet>
      <div className="fixed top-0 -z-10 h-full w-full">
      <div className="relative h-full w-full bg-slate-950"><div className="absolute bottom-0 left-[-20%] right-0 top-[-10%] h-[500px] w-[500px] rounded-full bg-[radial-gradient(circle_farthest-side,rgba(255,0,182,.15),rgba(255,255,255,0))]"></div><div className="absolute bottom-0 right-[-20%] top-[-10%] h-[500px] w-[500px] rounded-full bg-[radial-gradient(circle_farthest-side,rgba(255,0,182,.15),rgba(255,255,255,0))]"></div></div>
      </div>
      <div className="container mx-auto px-8">
        <Navbar />
        <Hero />
        <About />
        <Technologies />
        <Experience />
        <Projects />
        <Contact />
        <Copyright  />
      </div>
    </div>
  );
};

export default App;
