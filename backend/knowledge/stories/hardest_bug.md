# Digital Chandru - Behavioral Story (Hardest Bug)

## 1. The Bug
One of the hardest bugs I faced was maintaining stylistic continuity across AI-generated video scenes using the Veo model at Cloudside. Generative video models are stateless; they generate beautiful clips, but if you ask for "scene 2," the character, lighting, and style completely change. It made the multi-agent marketing pipeline produce disjointed, unusable ads.

## 2. The Debugging Process
At first, I tried fixing it via prompt engineering—stuffing the prompt with overly descriptive style details ("cinematic lighting, exact same red shirt, 4k"). It didn't work; the LLM's interpretation of text is too variable. I realized I couldn't solve a visual continuity problem with text. I needed to pass state visually.

## 3. The Fix
I stepped outside the LLM ecosystem and used standard computer vision. I engineered a programmatic feedback loop using OpenCV. After the video agent generated a scene, I extracted the absolute last frame of that `.mp4` file and injected it back into the multimodal prompt as the `initial_frame` for the next scene. This forced the Veo model to anchor its generation on the exact pixel state of the previous clip, creating flawless, continuous transitions. This taught me that the best AI solutions often involve traditional software engineering techniques.