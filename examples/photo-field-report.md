---
title: "Norwegian Fjord Decarbonization Field Report"
author: "text2pdf"
toc: true
---

[[image: Photorealistic editorial cover photo of a calm Norwegian fjord at sunrise, steep mountains mirrored in the water, a modern electric research vessel in the foreground, natural Nordic light, realistic atmosphere, high detail, magazine cover quality | alt=Front cover image of the fjord expedition | provider=gemini | aspect=16:9]]

# Norwegian Fjord Decarbonization Field Report

This example demonstrates image-rich PDF generation with a photorealistic front-page image and additional documentary-style images inside the report. It is designed to show how `--generate-images` can be combined with structured Markdown to produce a polished field report.

## Mission Context

The fictional mission follows a coastal research team measuring emissions, vessel traffic, and shoreline infrastructure in a western Norwegian fjord. The objective is to combine narrative reporting with visuals that feel like a real-world magazine or briefing document.

[[image: Photorealistic documentary photo of two marine researchers standing on the deck of a quiet electric ferry in a Norwegian fjord, one taking notes on a tablet while the other looks toward the shoreline, realistic weathered jackets, natural morning light, candid fieldwork atmosphere | alt=Research team on electric ferry | provider=gemini | aspect=16:9]]

## Key Findings

- Electric passenger ferries materially reduce local noise and visible exhaust in narrow fjord corridors
- Charging infrastructure placement is now a larger bottleneck than vessel availability
- Shoreline measurement stations need better weather protection and standardized maintenance windows

## Field Equipment

The field team relied on lightweight shoreline stations, compact water-quality sensors, and a rolling calibration kit stored onboard the support vessel.

[[image: Photorealistic close-up photo of a coastal water sampling station on a rocky Norwegian shoreline, stainless equipment, labeled tubes, small weatherproof instruments, sea spray on dark stone, crisp natural light, realistic technical documentary style | alt=Water sampling station on the shoreline | provider=gemini | aspect=4:3]]

## Snapshot Table

| Area | Status | Notes |
|------|--------|-------|
| Vessel electrification | Strong progress | Passenger routes have the clearest transition path |
| Grid readiness | Mixed | Rural charging points still lag behind port demand |
| Monitoring coverage | Improving | New sensors are easier to deploy but harder to maintain in bad weather |

## Narrative Summary

The cover image establishes the tone for the report, while the interior images provide context for people, equipment, and working conditions. Together they turn a plain technical memo into a document that reads more like a board-ready field briefing.

## Regenerate

Use the following pattern to rebuild this example:

`text2pdf convert examples/photo-field-report.md -o examples/photo-field-report.pdf --engine pandoc --theme report --generate-images --image-provider gemini --image-dir examples/photo-field-report_assets`