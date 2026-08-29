<div align="center">

<img src="assets/hero.svg" width="100%" alt="Three equal masses tracing a figure-eight choreography, flanked by two Keplerian orbital systems">

### **`Akshat Dalakoti`**

**Nothing in that banner is a keyframe.** It is a numerically integrated solution
to the three-body problem, baked frame-for-frame into SVG.

<a href="https://akshatdalakoti-stack.github.io/akshatdalakoti-stack/">
  <img src="https://img.shields.io/badge/▶_launch_the_live_simulation-05060f?style=for-the-badge&labelColor=7c5cff&color=05060f" alt="Launch the live simulation">
</a>

<sub>
  <a href="https://akshatdalakoti-stack.github.io/akshatdalakoti-stack/#eight">figure&#8209;8</a> ·
  <a href="https://akshatdalakoti-stack.github.io/akshatdalakoti-stack/#binary">binary</a> ·
  <a href="https://akshatdalakoti-stack.github.io/akshatdalakoti-stack/#collision">galaxy collision</a> ·
  <a href="https://akshatdalakoti-stack.github.io/akshatdalakoti-stack/#collapse">cold collapse</a>
</sub>

</div>

---

## About

<!-- Rewrite this paragraph in your own words. -->
I build things and take them apart to see why they worked. Most of what I enjoy
sits where clean maths meets something you can actually watch move — simulation,
graphics, embedded control, and the small tools that make the rest less painful.

- 🔭 Currently working on — *(fill in)*
- 🌱 Currently learning — *(fill in)*
- 💬 Ask me about — *(fill in)*
- 📫 Reach me at — **akshatdalakoti@gmail.com**

## Tech

<!-- Trim anything here you would rather not claim; badges are just image URLs. -->
<p>
  <img src="https://img.shields.io/badge/Python-05060f?style=flat-square&logo=python&logoColor=4cc9f0" alt="Python">
  <img src="https://img.shields.io/badge/C-05060f?style=flat-square&logo=c&logoColor=4cc9f0" alt="C">
  <img src="https://img.shields.io/badge/C++-05060f?style=flat-square&logo=cplusplus&logoColor=4cc9f0" alt="C++">
  <img src="https://img.shields.io/badge/JavaScript-05060f?style=flat-square&logo=javascript&logoColor=ffd166" alt="JavaScript">
  <img src="https://img.shields.io/badge/Go-05060f?style=flat-square&logo=go&logoColor=4cc9f0" alt="Go">
  <img src="https://img.shields.io/badge/NumPy-05060f?style=flat-square&logo=numpy&logoColor=7c5cff" alt="NumPy">
  <img src="https://img.shields.io/badge/Jupyter-05060f?style=flat-square&logo=jupyter&logoColor=ffd166" alt="Jupyter">
  <img src="https://img.shields.io/badge/Linux-05060f?style=flat-square&logo=linux&logoColor=ffd166" alt="Linux">
  <img src="https://img.shields.io/badge/Git-05060f?style=flat-square&logo=git&logoColor=ff8fd1" alt="Git">
  <img src="https://img.shields.io/badge/Arduino-05060f?style=flat-square&logo=arduino&logoColor=4cc9f0" alt="Arduino">
</p>

## Stats

<div align="center">

<img height="150" alt="GitHub stats" src="https://github-readme-stats.vercel.app/api?username=akshatdalakoti-stack&show_icons=true&hide_border=true&bg_color=05060f&title_color=7c5cff&icon_color=4cc9f0&text_color=b8c6ff">
<img height="150" alt="Top languages" src="https://github-readme-stats.vercel.app/api/top-langs/?username=akshatdalakoti-stack&layout=compact&hide_border=true&bg_color=05060f&title_color=7c5cff&text_color=b8c6ff">

<img height="150" alt="Contribution streak" src="https://streak-stats.demolab.com?user=akshatdalakoti-stack&hide_border=true&background=05060f&ring=7c5cff&fire=ffd166&currStreakLabel=4cc9f0&sideLabels=b8c6ff&dates=8b93b8&stroke=1c2040&currStreakNum=e8ecff&sideNums=e8ecff">

</div>

## Elsewhere

<p>
  <a href="https://github.com/akshatdalakoti-stack"><img src="https://img.shields.io/badge/GitHub-05060f?style=for-the-badge&logo=github&logoColor=b8c6ff" alt="GitHub"></a>
  <a href="mailto:akshatdalakoti@gmail.com"><img src="https://img.shields.io/badge/Email-05060f?style=for-the-badge&logo=gmail&logoColor=ffd166" alt="Email"></a>
  <!-- Add your own: LinkedIn, X, site, wherever. -->
</p>

---

## How the banner actually works

GitHub renders README images inside `<img>`, which means **no JavaScript**. So a
real-time simulation is impossible there — but a *pre-computed* one is not. The
banner is an SVG whose motion is genuine physics, solved ahead of time:

**The centre** is the Chenciner–Montgomery figure-eight choreography: three equal
masses chasing one another around a single closed curve. It is an exact periodic
solution of the Newtonian three-body problem, and it is the reason the loop is
seamless — the system really does return to its starting state. It is integrated
with RK4 from the canonical initial conditions in [`tools/gen_hero.py`](tools/gen_hero.py).

**The flanks** are true Keplerian two-body orbits. Each position comes from
solving Kepler's equation `M = E − e·sin(E)` by Newton–Raphson, so the bodies
visibly accelerate at periapsis and loiter at apoapsis, exactly as Kepler's
second law requires. The three satellites per system are in a 1:2:3 resonance,
so they too close the loop together.

Two details make it small enough to ship (**80 KB**, down from 1 MB):

- Each orbit is one `<path>`, shared by every element that follows it. The
  physical *timing* rides in `keyPoints`/`keyTimes` — arc-length travelled
  against fraction of period. The path stays high-resolution; the timing curve
  is smooth, so it can be sampled coarsely without any visible error.
- The comet tails are not particles. Each is a single dashed stroke whose dash
  is exactly the tail length and whose gap fills the rest of the closed orbit,
  so the pattern wraps seamlessly. Animating `stroke-dashoffset` along that same
  timing curve makes the tail stretch and bunch with the body's real speed —
  three elements per body instead of twenty ghost dots.

Regenerate it with:

```bash
python tools/gen_hero.py
```

The [live version](https://akshatdalakoti-stack.github.io/akshatdalakoti-stack/)
drops the pre-computation and integrates in the browser instead — velocity
Verlet with Plummer softening, momentum-conserving merges, and your cursor as a
gravity well. Drag to slingshot a new world into orbit.

<div align="center"><sub>Built with an unreasonable amount of care for a README.</sub></div>
