# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Stack

Delegated after offering a stack choice: a local Python web application using Qiskit, Qiskit Optimization, and Qiskit Aer. Prefer free, installable dependencies and no required cloud service or quantum hardware.

## Users

Researchers and technically curious users studying ACO, combinatorial optimization, and quantum optimization.

## Product Purpose

An interactive Vietnamese-language website for learning about ACO and experimenting with a genuine quantum optimization approach on small TSP instances. Success means users can inspect how each method works, change experiment inputs, run both methods, and understand the limits of any comparison.

## Positioning

The website compares classical Ant Colony Optimization with QAOA formulated for TSP using Qiskit. QAOA is a distinct quantum optimization method, not a quantum implementation of ACO; the website must make that distinction explicit.

## Operating Context

Users configure small TSP experiments, run ACO and QAOA on a local simulator, inspect routes and measurement results, and consult primary scientific and official framework references.

## Capabilities and Constraints

- The quantum implementation uses Qiskit and a free local simulator; actual quantum hardware is not required.
- Simulator results are experimental and instance-, parameter-, and shot-dependent. Do not promise quantum speedup or general superiority.
- The quantum experiment is limited to small instances that are practical for local statevector or shot-based simulation.
- Use reproducible seeds where supported and disclose solver settings and execution limitations.
- Do not fabricate benchmark evidence, citations, measured performance, or claims of quantum advantage.

## Evidence on Hand

The workspace contains a standard-library ACO implementation and its tests in `aco_quantum.py` and `test_aco_quantum.py`. It contains no product research or benchmark data. Scientific and framework claims must be supported by traceable scholarly or official sources in the website.

## Product Principles

- Distinguish algorithm families and claims precisely.
- Make the experiment inspectable and reproducible.
- Show assumptions, limitations, and measurement variability alongside results.
- Prefer primary scientific literature and official framework documentation.
