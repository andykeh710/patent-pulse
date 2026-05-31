// 6 starter topic packs users can create with one click.
// Each mirrors the topicsApi.create() payload shape.

export interface StarterTopic {
  name: string;
  description: string;
  cpc_prefixes: string[];
  keywords?: string[];
  icon: string; // emoji for the card
}

export const STARTER_TOPICS: StarterTopic[] = [
  {
    name: "AI & Machine Learning",
    description: "Neural networks, model architectures, training systems, inference hardware",
    cpc_prefixes: ["G06N", "G06F", "G06V"],
    keywords: ["neural network", "deep learning", "transformer", "LLM", "inference"],
    icon: "🧠",
  },
  {
    name: "Clean Energy & Batteries",
    description: "Renewable energy, battery chemistry, EV power systems, grid storage",
    cpc_prefixes: ["Y02E", "H01M", "H02J"],
    keywords: ["lithium", "solid-state battery", "solar cell", "fuel cell", "energy storage"],
    icon: "⚡",
  },
  {
    name: "Biotech & Pharma",
    description: "Gene therapy, monoclonal antibodies, drug delivery, CRISPR, mRNA",
    cpc_prefixes: ["C12N", "C07K", "A61K"],
    keywords: ["antibody", "gene therapy", "CRISPR", "mRNA", "peptide"],
    icon: "🧬",
  },
  {
    name: "Wireless & Telecom",
    description: "5G/6G, beamforming, network slicing, IoT protocols, satellite comms",
    cpc_prefixes: ["H04W", "H04L", "H04B"],
    keywords: ["5G", "beamforming", "MIMO", "OFDM", "network slicing"],
    icon: "📡",
  },
  {
    name: "Medical Devices",
    description: "Surgical instruments, implants, diagnostics, wearables, imaging",
    cpc_prefixes: ["A61B", "A61F", "A61M"],
    keywords: ["implant", "catheter", "stent", "endoscope", "wearable sensor"],
    icon: "🩺",
  },
  {
    name: "Semiconductors",
    description: "Chip fabrication, lithography, packaging, power semiconductors, 3D stacking",
    cpc_prefixes: ["H01L", "H10W", "H05K"],
    keywords: ["finFET", "EUV", "chiplets", "3D stacking", "GaN", "SiC"],
    icon: "💾",
  },
];
