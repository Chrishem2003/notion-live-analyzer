
"""
Theoretical-to-Practical Protocol Transpiler
Converts dense paper methodology into actionable step-by-step laboratory,
computational, or data analysis protocols.

Core Capabilities:
  - Extracts chemical concentrations, gene accession codes, sequence pipelines
  - Extracts reagents, hardware/software execution parameters
  - Generates interactive workbench checklists with timer presets
  - Generates copyable bash/python code blocks
  - Step-by-step protocol formatting with safety notes
"""
from __future__ import annotations

import re
import json
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta

import pandas as pd


# Ã¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢Â
# 1. PROTOCOL EXTRACTION PATTERNS
# Ã¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢Â

EXTRACTION_PATTERNS = {
    "chemicals_reagents": [
        r"(\d(?:\.\d)?)\s*(?:mM|mM|Ã‚ÂµM|nM|mM|M|mg/mL|g/L|%)\s(?:of\s)?([A-Za-z0-9\s\-]?)(?=[,.;])",
        r"([A-Za-z0-9\s\-]?)\s*\((\d(?:\.\d)?)\s*(?:mM|mM|Ã‚ÂµM|nM|mM|M|mg/mL|g/L|%)\)",
        r"\b(DMSO|PBS|TBS|SDS|EDTA|EGTA|HEPES|Tris|NaCl|KCl|MgCl2|CaCl2|NaOH|HCl|H2SO4|EtOH|MeOH|IPA|DTT|BME|BSA|FBS|RPMI|DMEM|PFA|TBST)\b",
    ],
    "temperatures": [
        r"(\d(?:\.\d)?)\s*Ã‚Â°[Cc]",
        r"(\d(?:\.\d)?)\s*Ã‚Â°[Ff]",
        r"(?:at|to|for)\s(\d(?:\.\d)?)\s*Ã‚Â°",
        r"(?:incubat|heat|cool|warm|maintain)\s(?:at|to|for)\s(\d(?:\.\d)?)\s*Ã‚Â°",
    ],
    "time_durations": [
        r"(\d)\s*(?:min|minute|minutes|h|hour|hours|sec|second|seconds|d|day|days)",
        r"(?:for|after|during)\s(\d)\s*(?:min|h|sec|d)",
        r"(?:incubat|centrifug|spin|heat|treat)\s(?:for\s)?(\d)\s*(?:min|h|sec)",
    ],
    "centrifugation": [
        r"(\d(?:,\d{3})?)\s*(?:Ãƒâ€”?\s*g|g|rpm|RPM|x\s*g)\s(?:for\s)?(\d)\s*(?:min|h)",
        r"(?:centrifug|spin|pellet)\s(?:at\s)?(\d(?:,\d{3})?)\s*(?:g|rpm)",
    ],
    "gene_accessions": [
        r"\b(NM_\d{6,9})\b",
        r"\b(NG_\d{6,9})\b",
        r"\b(NR_\d{6,9})\b",
        r"\b(XM_\d{6,9})\b",
        r"\b(XR_\d{6,9})\b",
        r"\b(XP_\d{6,9})\b",
        r"\b(NP_\d{6,9})\b",
        r"\b(ENSG\d{11})\b",
        r"\b(ENST\d{11})\b",
        r"\b(ENSP\d{11})\b",
        r"\b(UniProt[:\s]*[A-Z0-9]{6,10})\b",
        r"\b(GeneID[:\s]*\d)\b",
        r"\b(GSE\d{4,6})\b",
        r"\b(GSM\d{4,6})\b",
        r"\b(GPL\d{4,6})\b",
        r"\b(SRR\d{6,10})\b",
        r"\b(ERR\d{6,10})\b",
        r"\b(PRJNA\d{6,10})\b",
        r"\b(PRJEB\d{6,10})\b",
    ],
    "software_tools": [
        r"\b(?:using|with|via|by)\s([A-Z][a-zA-Z0-9](?:[-\s][A-Z][a-zA-Z0-9])*)\s(?:software|package|tool|pipeline|version)",
        r"\b([A-Za-z0-9](?:[-_][A-Za-z0-9])*)\sv(?:\d\.\d(?:\.\d)?)",
        r"\b(BLAST|Bowtie|STAR|HISAT2|Salmon|Kallisto|DESeq2|edgeR|limma|Seurat|Scanpy|CellRanger|SPAdes|MEGAHIT|Trimmomatic|FastQC|MultiQC|Samtools|Bamtools|GATK|BCFtools|VCFtools|PLINK|PAUP|RAxML|MrBayes|BEAST|MEGA|IQ[- ]TREE|MAFFT|Clustal[O,W]|MUSCLE|T-Coffee)\b",
        r"\b(Python|R|MATLAB|Perl|Julia|Bash|C\\|Java)\s(?:script|code|program|implementation)",
    ],
    "hardware": [
        r"(?:using|with|on|via)\s(?:an?\s)?([A-Z][a-zA-Z0-9\s\-](?:microscope|sequencer|centrifuge|incubator|PCR|thermocycler|spectrophotometer|plate\s*reader|chromatograph))",
        r"\b(Illumina|PacBio|Oxford\sNanopore|454|Ion\sTorrent|HiSeq|MiSeq|NovaSeq|NextSeq|MinION|PromethION)\b",
        r"\b(?:flow\scytometer|FACS|HPLC|LC-MS|GC-MS|NMR|MRI|CT\sscan|X-ray)\b",
    ],
    "statistical_params": [
        r"(?:ÃŽÂ±|alpha)\s*=\s*(\d\.?\d*)",
        r"(?:ÃŽÂ²|beta)\s*=\s*(\d\.?\d*)",
        r"power\s*=\s*(\d\.?\d*)",
        r"effect\ssize\s*=\s*(\d\.?\d*)",
        r"(?:FDR|q-value|adjusted\sp)\s*[<Ã¢â€°Â¤]\s*(\d\.?\d*)",
        r"(?:p\s*[<Ã¢â€°Â¤]\s*(\d\.?\d*))",
    ],
    "concentrations": [
        r"(\d(?:\.\d)?)\s*(?:Ã‚Âµg|ng|mg|g)\s*/?\s*(?:mL|Ã‚ÂµL|L)",
        r"(\d(?:\.\d)?)\s*(?:mM|Ã‚ÂµM|nM|pM|M)\s[A-Za-z]",
        r"(?:concentration|dose|dosage)\s(?:of\s)?(\d(?:\.\d)?)\s*(?:Ã‚Âµg|ng|mg|g|mM|Ã‚ÂµM|nM)",
    ],
}


# Protocol section templates
PROTOCOL_SECTIONS = [
    "Title",
    "Objective",
    "Materials & Reagents",
    "Equipment",
    "Software & Data",
    "Safety Precautions",
    "Step-by-Step Protocol",
    "Expected Outcomes",
    "Troubleshooting",
    "References",
]


class ProtocolTranspiler:
    """
    Converts research methodology text into structured, actionable protocols.
    """

    def __init__(self):
        self.patterns = EXTRACTION_PATTERNS

    def transpile(self, text: str, protocol_title: str = "") -> Dict[str, Any]:
        """
        Full transpilation pipeline  extracts all parameters and builds protocol.

        Args:
            text: Methodology text to transpile
            protocol_title: Optional title for the protocol

        Returns:
            Dict with structured protocol data
        """
        if not text or not text.strip():
            return {"error": "No methodology text provided"}

        results = {
            "title": protocol_title or "Extracted Protocol",
            "extracted_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "reagents": self._extract_reagents(text),
            "temperatures": self._extract_temperatures(text),
            "durations": self._extract_durations(text),
            "centrifugation": self._extract_centrifugation(text),
            "gene_accessions": self._extract_gene_accessions(text),
            "software": self._extract_software(text),
            "hardware": self._extract_hardware(text),
            "concentrations": self._extract_concentrations(text),
            "statistical_params": self._extract_statistical_params(text),
            "steps": self._generate_steps(text),
            "checklist": self._generate_checklist(text),
            "code_blocks": self._extract_code_blocks(text),
            "bib_citations": self._extract_citations(text),
            "safety_notes": self._extract_safety_notes(text),
        }

        # Calculate summary stats
        results["summary"] = {
            "total_reagents": len(results["reagents"]),
            "total_steps": len(results["steps"]),
            "total_tools": len(results["software"]) + len(results["hardware"]),
            "has_code": len(results["code_blocks"]) > 0,
            "has_safety": len(results["safety_notes"]) > 0,
        }

        return results

    def _extract_reagents(self, text: str) -> List[Dict[str, Any]]:
        """Extract chemicals, reagents, and materials."""
        reagents = []
        seen = set()

        for pattern in self.patterns["chemicals_reagents"]:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for m in matches:
                reagent = m.group(0).strip()
                if reagent.lower() not in seen:
                    seen.add(reagent.lower())
                    reagents.append({
                        "name": reagent,
                        "concentration": m.group(1) if m.lastindex and m.lastindex >= 1 else "",
                        "category": "chemical" if len(reagent) > 2 else "buffer",
                    })

        # Deduplicate and sort by specificity
        return sorted(reagents, key=lambda r: -len(r["name"]))[:30]

    def _extract_temperatures(self, text: str) -> List[Dict[str, str]]:
        """Extract temperature conditions."""
        temps = []
        for pattern in self.patterns["temperatures"]:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for m in matches:
                value = m.group(1)
                temps.append({
                    "value": f"{value}Ã‚Â°C",
                    "context": self._get_context(text, m.start(), 60),
                })
        return temps[:10]

    def _extract_durations(self, text: str) -> List[Dict[str, str]]:
        """Extract time durations."""
        durations = []
        for pattern in self.patterns["time_durations"]:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for m in matches:
                durations.append({
                    "value": m.group(0).strip(),
                    "context": self._get_context(text, m.start(), 60),
                })
        return durations[:15]

    def _extract_centrifugation(self, text: str) -> List[Dict[str, str]]:
        """Extract centrifugation conditions."""
        spins = []
        for pattern in self.patterns["centrifugation"]:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for m in matches:
                spins.append({
                    "condition": m.group(0).strip(),
                    "context": self._get_context(text, m.start(), 60),
                })
        return spins[:5]

    def _extract_gene_accessions(self, text: str) -> List[Dict[str, str]]:
        """Extract gene/sequence accession IDs."""
        accessions = []
        for pattern in self.patterns["gene_accessions"]:
            matches = re.finditer(pattern, text)
            for m in matches:
                accessions.append({
                    "accession": m.group(0).strip(),
                    "database": self._identify_database(m.group(0)),
                })
        return accessions[:20]

    def _extract_software(self, text: str) -> List[Dict[str, str]]:
        """Extract software tools and versions."""
        tools = []
        for pattern in self.patterns["software_tools"]:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for m in matches:
                tools.append({
                    "name": m.group(0).strip(),
                    "context": self._get_context(text, m.start(), 80),
                })
        return tools[:15]

    def _extract_hardware(self, text: str) -> List[Dict[str, str]]:
        """Extract hardware/equipment."""
        hardware = []
        for pattern in self.patterns["hardware"]:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for m in matches:
                hardware.append({
                    "device": m.group(0).strip(),
                    "context": self._get_context(text, m.start(), 80),
                })
        return hardware[:10]

    def _extract_concentrations(self, text: str) -> List[Dict[str, str]]:
        """Extract concentration values."""
        concs = []
        for pattern in self.patterns["concentrations"]:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for m in matches:
                concs.append({
                    "value": m.group(0).strip(),
                    "context": self._get_context(text, m.start(), 60),
                })
        return concs[:15]

    def _extract_statistical_params(self, text: str) -> List[Dict[str, str]]:
        """Extract statistical parameters."""
        params = []
        for pattern in self.patterns["statistical_params"]:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for m in matches:
                params.append({
                    "parameter": m.group(0).strip(),
                    "context": self._get_context(text, m.start(), 60),
                })
        return params[:10]

    def _generate_steps(self, text: str) -> List[Dict[str, Any]]:
        """Generate actionable protocol steps from methodology text."""
        # Split text into sentences and categorize
        sentences = re.split(r'[.!?]\s', text)
        steps = []
        step_num = 0

        for sent in sentences:
            sent = sent.strip()
            if not sent or len(sent) < 20:
                continue

            # Categorize the step
            category = self._categorize_sentence(sent)
            if category:
                step_num = 1
                steps.append({
                    "step_number": step_num,
                    "instruction": sent,
                    "category": category,
                    "estimated_duration": self._estimate_duration(sent),
                    "safety_notes": self._extract_safety_from_sentence(sent),
                })

        return steps[:25]

    def _categorize_sentence(self, sentence: str) -> Optional[str]:
        """Categorize a methodology sentence."""
        s_lower = sentence.lower()

        if any(w in s_lower for w in ["incubat", "heat", "cool", "warm", "temperatur"]):
            return "incubation"
        if any(w in s_lower for w in ["centrifug", "spin", "pellet"]):
            return "centrifugation"
        if any(w in s_lower for w in ["add", "mix", "combine", "suspend", "dissolve"]):
            return "mixing"
        if any(w in s_lower for w in ["wash", "rinse", "elute", "purif"]):
            return "washing"
        if any(w in s_lower for w in ["extract", "isolate", "separat"]):
            return "extraction"
        if any(w in s_lower for w in ["amplif", "pcr", "qpcr", "rt-pcr"]):
            return "amplification"
        if any(w in s_lower for w in ["sequenc", "ngs", "rna-seq", "chip-seq"]):
            return "sequencing"
        if any(w in s_lower for w in ["stain", "label", "probe", "antibod"]):
            return "staining"
        if any(w in s_lower for w in ["measur", "analyz", "quantif"]):
            return "measurement"
        if any(w in s_lower for w in ["normaliz", "transform", "standardiz"]):
            return "normalization"
        if any(w in s_lower for w in ["run", "execut", "launch", "comput"]):
            return "computation"
        if any(w in s_lower for w in ["collect", "harvest", "gather"]):
            return "collection"
        if any(w in s_lower for w in ["filter", "centrifug", "precipit"]):
            return "purification"
        if any(w in s_lower for w in ["transfect", "transform", "transduc"]):
            return "transfection"

        return "general"

    def _estimate_duration(self, sentence: str) -> Optional[str]:
        """Estimate step duration from sentence."""
        duration_patterns = [
            (r"(\d)\s*(?:h|hour)s?\s(\d)\s*(?:min|minute)", lambda m: f"{m.group(1)}h {m.group(2)}min"),
            (r"(\d)\s*(?:h|hour)s?", lambda m: f"{m.group(1)} hours"),
            (r"(\d)\s*(?:min|minute)s?", lambda m: f"{m.group(1)} min"),
            (r"(\d)\s*(?:sec|second)s?", lambda m: f"{m.group(1)} sec"),
            (r"(\d)\s*(?:d|day)s?", lambda m: f"{m.group(1)} days"),
        ]
        for pattern, formatter in duration_patterns:
            m = re.search(pattern, sentence, re.IGNORECASE)
            if m:
                return formatter(m)
        return None

    def _generate_checklist(self, text: str) -> List[Dict[str, Any]]:
        """Generate an interactive workbench checklist."""
        checklist = []

        # Reagent checklist
        reagents = self._extract_reagents(text)
        for r in reagents:
            checklist.append({
                "item": r["name"],
                "category": "reagent",
                "prepared": False,
                "notes": r.get("concentration", ""),
            })

        # Equipment checklist
        hardware = self._extract_hardware(text)
        for h in hardware:
            checklist.append({
                "item": h["device"],
                "category": "equipment",
                "prepared": False,
                "notes": "",
            })

        # Software checklist
        software = self._extract_software(text)
        for s in software:
            checklist.append({
                "item": s["name"],
                "category": "software",
                "prepared": False,
                "notes": "",
            })

        # Safety checklist
        safety = self._extract_safety_notes(text)
        for s in safety:
            checklist.append({
                "item": s,
                "category": "safety",
                "prepared": False,
                "notes": "Ã¢Å¡Â Ã¯Â¸Â Safety critical",
            })

        return checklist[:30]

    def _extract_code_blocks(self, text: str) -> List[Dict[str, str]]:
        """Extract code blocks or command-line instructions."""
        code_blocks = []

        # Python/R/bash code patterns
        code_patterns = [
            (r"```(\w)?\n(.*?)```", re.DOTALL),
            (r"`([^`])`", 0),
            (r"(?:command|code|script|syntax)[:\s]([^\n])", 0),
            (r"(?:pip install|conda install|git clone|wget|curl|docker|singularity)\s\S", 0),
            (r"(?:library\(|import\s\w|require\(|using\s\w)", 0),
        ]

        for pattern, flags in code_patterns:
            matches = re.finditer(pattern, text, flags)
            for m in matches:
                code = m.group(1) if m.lastindex else m.group(0)
                if code.strip():
                    lang = ""
                    if "```" in m.group(0):
                        lang = m.group(1) or "unknown"
                    code_blocks.append({
                        "language": lang,
                        "code": code.strip(),
                        "context": self._get_context(text, m.start(), 40),
                    })

        return code_blocks[:10]

    def _extract_citations(self, text: str) -> List[str]:
        """Extract in-text citations."""
        citations = []
        patterns = [
            r"\([A-Z][a-z](?:\set\sal\.?)?,\s*\d{4}[^)]*\)",
            r"[A-Z][a-z](?:\set\sal\.?)?\s*\(\d{4}\)",
            r"\[\d(?:[,Ã¢â‚¬â€œ]\d)*\]",
        ]
        for pattern in patterns:
            matches = re.findall(pattern, text)
            citations.extend(matches)
        return citations[:10]

    def _extract_safety_notes(self, text: str) -> List[str]:
        """Extract safety-related information."""
        safety_phrases = [
            r"(?:wear|use|put\son)\s(?:gloves|goggles|lab\scoat|PPE|face\sshield|mask)",
            r"(?:handle|work)\s(?:with|in)\s(?:carefully|cautiously|fume\shood|biosafety)",
            r"(?:toxic|carcinogen|hazardous|flammable|corrosive|biohazard|radioactive)",
            r"(?:dispose|discard|waste)\s(?:properly|according|safely|in\sappropriate)",
            r"(?:autoclave|steriliz|decontaminat|bleach|ethanol\s70)",
            r"(?:MSDS|SDS|safety\sdata\ssheet|biosafety\slevel|BSL-\d)",
        ]
        notes = []
        for pattern in safety_phrases:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for m in matches:
                notes.append(m.strip().capitalize())
        return list(set(notes))

    def _extract_safety_from_sentence(self, sentence: str) -> List[str]:
        """Extract safety notes from a single sentence."""
        notes = []
        if re.search(r"(toxic|carcinogen|hazardous|flammable|corrosive)", sentence, re.IGNORECASE):
            notes.append("Ã¢Å¡Â Ã¯Â¸Â Handle hazardous material with appropriate PPE")
        if re.search(r"centrifug|high\s*speed|ultracentrifug", sentence, re.IGNORECASE):
            notes.append("Ã¢Å¡Â Ã¯Â¸Â Balance tubes before centrifugation")
        if re.search(r"(heat|incubat)\s(?:to\s)?(\d)", sentence, re.IGNORECASE):
            temp_match = re.search(r"(\d)", sentence)
            if temp_match and int(temp_match.group(1)) > 60:
                notes.append("Ã¢Å¡Â Ã¯Â¸Â Use heat-resistant gloves for hot equipment")
        if re.search(r"(electrophoresis|gel|voltage|current)", sentence, re.IGNORECASE):
            notes.append("Ã¢Å¡Â Ã¯Â¸Â Ensure electrophoresis lid is properly closed")
        return notes

    def _identify_database(self, accession: str) -> str:
        """Identify the database for a given accession code."""
        accession = accession.upper()
        if accession.startswith("NM_") or accession.startswith("NR_"):
            return "RefSeq (NCBI)"
        if accession.startswith("NG_"):
            return "RefSeq Genome (NCBI)"
        if accession.startswith("XM_") or accession.startswith("XR_"):
            return "RefSeq Predicted (NCBI)"
        if accession.startswith("XP_") or accession.startswith("NP_"):
            return "RefSeq Protein (NCBI)"
        if accession.startswith("ENSG"):
            return "Ensembl Gene"
        if accession.startswith("ENST"):
            return "Ensembl Transcript"
        if accession.startswith("ENSP"):
            return "Ensembl Protein"
        if accession.startswith("GSE") or accession.startswith("GSM") or accession.startswith("GPL"):
            return "GEO (NCBI)"
        if accession.startswith("SRR") or accession.startswith("ERR"):
            return "SRA (NCBI)"
        if accession.startswith("PRJNA") or accession.startswith("PRJEB"):
            return "BioProject (NCBI/EBI)"
        if "UNIPROT" in accession:
            return "UniProt"
        return "Unknown Database"

    def _get_context(self, text: str, pos: int, window: int = 60) -> str:
        """Get surrounding context for a match."""
        start = max(0, pos - window)
        end = min(len(text), pos + window)
        context = text[start:end].strip()
        if start > 0:
            context = "..." + context
        if end < len(text):
            context = context + "..."
        return context

    def format_protocol_text(self, protocol: Dict[str, Any]) -> str:
        """Format the protocol as a structured text document."""
        lines = [
            "Ã¢â€¢Â" * 70,
            f"PROTOCOL: {protocol.get('title', 'Untitled Protocol')}",
            f"Generated: {protocol.get('extracted_at', 'N/A')}",
            "Ã¢â€¢Â" * 70,
            "",
        ]

        # Materials & Reagents
        reagents = protocol.get("reagents", [])
        if reagents:
            lines.append("Ã¢â€â‚¬" * 40)
            lines.append("MATERIALS & REAGENTS")
            lines.append("Ã¢â€â‚¬" * 40)
            for r in reagents:
                lines.append(f"  Ã¢â‚¬Â¢ {r['name']}")
            lines.append("")

        # Temperatures
        temps = protocol.get("temperatures", [])
        if temps:
            lines.append("Ã¢â€â‚¬" * 40)
            lines.append("TEMPERATURE CONDITIONS")
            lines.append("Ã¢â€â‚¬" * 40)
            for t in temps:
                lines.append(f"  Ã¢â‚¬Â¢ {t['value']}  {t['context']}")
            lines.append("")

        # Durations
        durations = protocol.get("durations", [])
        if durations:
            lines.append("Ã¢â€â‚¬" * 40)
            lines.append("TIME PARAMETERS")
            lines.append("Ã¢â€â‚¬" * 40)
            for d in durations:
                lines.append(f"  Ã¢â‚¬Â¢ {d['value']}")
            lines.append("")

        # Centrifugation
        spins = protocol.get("centrifugation", [])
        if spins:
            lines.append("Ã¢â€â‚¬" * 40)
            lines.append("CENTRIFUGATION CONDITIONS")
            lines.append("Ã¢â€â‚¬" * 40)
            for s in spins:
                lines.append(f"  Ã¢â‚¬Â¢ {s['condition']}")
            lines.append("")

        # Gene Accessions
        accessions = protocol.get("gene_accessions", [])
        if accessions:
            lines.append("Ã¢â€â‚¬" * 40)
            lines.append("GENE / SEQUENCE ACCESSION IDs")
            lines.append("Ã¢â€â‚¬" * 40)
            for a in accessions:
                lines.append(f"  Ã¢â‚¬Â¢ {a['accession']} ({a['database']})")
            lines.append("")

        # Software
        software = protocol.get("software", [])
        if software:
            lines.append("Ã¢â€â‚¬" * 40)
            lines.append("SOFTWARE & TOOLS")
            lines.append("Ã¢â€â‚¬" * 40)
            for s in software:
                lines.append(f"  Ã¢â‚¬Â¢ {s['name']}")
            lines.append("")

        # Hardware
        hardware = protocol.get("hardware", [])
        if hardware:
            lines.append("Ã¢â€â‚¬" * 40)
            lines.append("EQUIPMENT / HARDWARE")
            lines.append("Ã¢â€â‚¬" * 40)
            for h in hardware:
                lines.append(f"  Ã¢â‚¬Â¢ {h['device']}")
            lines.append("")

        # Step-by-step protocol
        steps = protocol.get("steps", [])
        if steps:
            lines.append("Ã¢â€â‚¬" * 40)
            lines.append("STEP-BY-STEP PROTOCOL")
            lines.append("Ã¢â€â‚¬" * 40)
            for step in steps:
                duration = f" [{step.get('estimated_duration', '')}]" if step.get("estimated_duration") else ""
                lines.append(f"\n  Step {step['step_number']}{duration}")
                lines.append(f"  {step['instruction']}")
                if step.get("safety_notes"):
                    for note in step["safety_notes"]:
                        lines.append(f"    {note}")
            lines.append("")

        # Code blocks
        code_blocks = protocol.get("code_blocks", [])
        if code_blocks:
            lines.append("Ã¢â€â‚¬" * 40)
            lines.append("CODE / COMMAND BLOCKS")
            lines.append("Ã¢â€â‚¬" * 40)
            for cb in code_blocks:
                lang = f" ({cb['language']})" if cb.get("language") else ""
                lines.append(f"\n{lang}:")
                lines.append(f"  ```{cb['language']}")
                lines.append(f"  {cb['code']}")
                lines.append("  ```")
            lines.append("")

        # Safety notes
        safety = protocol.get("safety_notes", [])
        if safety:
            lines.append("Ã¢â€â‚¬" * 40)
            lines.append("SAFETY PRECAUTIONS")
            lines.append("Ã¢â€â‚¬" * 40)
            for s in safety:
                lines.append(f"  Ã¢Å¡Â Ã¯Â¸Â {s}")
            lines.append("")

        # Bibliography
        citations = protocol.get("bib_citations", [])
        if citations:
            lines.append("Ã¢â€â‚¬" * 40)
            lines.append("REFERENCES")
            lines.append("Ã¢â€â‚¬" * 40)
            for c in citations:
                lines.append(f"  Ã¢â‚¬Â¢ {c}")
            lines.append("")

        lines.append("Ã¢â€¢Â" * 70)
        lines.append("END OF PROTOCOL")
        lines.append("Ã¢â€¢Â" * 70)

        return "\n".join(lines)

    def generate_bash_commands(self, protocol: Dict[str, Any]) -> List[str]:
        """Generate copyable bash commands from software tools."""
        commands = []
        for tool in protocol.get("software", []):
            name = tool["name"].lower()
            if "python" in name:
                commands.append("#!/bin/bash")
                commands.append("# Python environment setup")
                commands.append("python --version")
                commands.append("pip install -r requirements.txt")
            elif "r " in name or "r/" in name or name.strip() == "r":
                commands.append("# R environment")
                commands.append("R --version")
                commands.append("Rscript analysis.R")
            elif "blast" in name:
                commands.append("# BLAST search")
                commands.append("blastn -query query.fasta -db nt -out results.txt")
            elif "bowtie" in name or "star" in name or "hisat" in name:
                commands.append(f"# {tool['name']} alignment")
                commands.append(f"{tool['name'].lower().replace(' ', '').replace('-', '')} --genomeDir /path/to/index --readFilesIn sample_R1.fastq --outFileNamePrefix sample_")
            elif "fastqc" in name:
                commands.append("# Quality control")
                commands.append("fastqc *.fastq -o qc_reports/")
            elif "trimmomatic" in name or "cutadapt" in name:
                commands.append("# Read trimming")
                commands.append("trimmomatic PE sample_R1.fastq sample_R2.fastq sample_trimmed_R1.fastq sample_trimmed_R2.fastq ILLUMINACLIP:adapters.fa:2:30:10 LEADING:3 TRAILING:3 SLIDINGWINDOW:4:15 MINLEN:36")

        if not commands:
            commands.append("# No specific commands could be generated from the methodology")
            commands.append("# Install required dependencies:")
            commands.append("pip install -r requirements.txt")

        return commands


# Ã¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢Â
# 3. UI RENDERER
# Ã¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢Â
def render_lab_protocol_transpiler_ui():
    """Render the Lab Protocol Transpiler UI."""
    import streamlit as st

    st.markdown("## Ã°Å¸Â§Âª Theoretical-to-Practical Protocol Transpiler")
    st.markdown("*Converts dense paper methodology into actionable step-by-step protocols with reagents, equipment, code blocks, and safety notes*")

    tab1, tab2, tab3 = st.tabs(["Ã°Å¸â€œÂ Input & Transpile", "ðŸ“‹ Full Protocol", "Ã°Å¸â€™Â» Code & Commands"])

    transpiler = ProtocolTranspiler()

    with tab1:
        st.subheader("Ã°Å¸â€œÂ Enter Methodology Text")

        text = st.text_area(
            "Paste methodology text from a paper:",
            height=250,
            placeholder="Example: Cells were cultured in DMEM supplemented with 10% FBS and 1% penicillin-streptomycin at 37Ã‚Â°C. Total RNA was extracted using TRIzol reagent. RNA purity was assessed using a NanoDrop spectrophotometer. cDNA was synthesized from 1Ã‚Âµg RNA using the iScript cDNA Synthesis Kit. qPCR was performed using SYBR Green Master Mix on a CFX96 thermal cycler with the following conditions: 95Ã‚Â°C for 3 min, followed by 40 cycles of 95Ã‚Â°C for 10s and 60Ã‚Â°C for 30s. Relative expression was calculated using the 2^-ÃŽâ€ÃŽâ€Ct method with GAPDH as a reference gene. All experiments were performed in triplicate...",
            key="protocol_input_text",
        )

        title = st.text_input("Protocol title (optional)", placeholder="e.g., RNA Extraction & qPCR Protocol", key="protocol_title")

        col1, col2 = st.columns([3, 1])
        with col1:
            run = st.button("Ã°Å¸Â§Âª Transpile to Protocol", type="primary", use_container_width=True)
        with col2:
            st.caption(f"Chars: {len(text):,}")

        if run and text.strip():
            with st.spinner("Transpiling methodology..."):
                protocol = transpiler.transpile(text, protocol_title=title)
                st.session_state["_last_protocol"] = protocol

            summary = protocol.get("summary", {})
            st.success(f"âœ… Protocol generated! {summary.get('total_steps', 0)} steps, {summary.get('total_reagents', 0)} reagents, {summary.get('total_tools', 0)} tools")

            st.subheader("Quick Overview")
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Steps", summary.get("total_steps", 0))
            with col2:
                st.metric("Reagents", summary.get("total_reagents", 0))
            with col3:
                st.metric("Tools", summary.get("total_tools", 0))
            with col4:
                st.metric("Code Blocks", len(protocol.get("code_blocks", [])))

            # Show extracted items
            if protocol.get("reagents"):
                with st.expander("Ã°Å¸Â§Âª Extracted Reagents"):
                    for r in protocol["reagents"]:
                        st.markdown(f"- {r['name']}")

            if protocol.get("gene_accessions"):
                with st.expander("Ã°Å¸Â§Â¬ Gene/Sequence Accessions"):
                    for a in protocol["gene_accessions"]:
                        st.markdown(f"- {a['accession']} ({a['database']})")

            if protocol.get("temperatures"):
                with st.expander("Ã°Å¸Å’Â¡Ã¯Â¸Â Temperature Conditions"):
                    for t in protocol["temperatures"]:
                        st.markdown(f"- {t['value']}: {t['context']}")

            if protocol.get("safety_notes"):
                with st.expander("Ã¢Å¡Â Ã¯Â¸Â Safety Notes"):
                    for s in protocol["safety_notes"]:
                        st.warning(s)

        elif run:
            st.warning("Please paste methodology text first.")

    with tab2:
        protocol = st.session_state.get("_last_protocol")
        if not protocol:
            st.info("Transpile a protocol first in the **Input & Transpile** tab.")
        else:
            st.subheader("ðŸ“‹ Complete Protocol")

            protocol_text = transpiler.format_protocol_text(protocol)
            st.markdown(f"```\n{protocol_text}\n```")

            import base64
            b64 = base64.b64encode(protocol_text.encode()).decode()
            st.markdown(
                f'<a href="data:text/plain;base64,{b64}" download="protocol.txt" '
                f'style="display:inline-block;padding:10px 20px;background:#1d4ed8;color:white;'
                f'border-radius:8px;text-decoration:none;font-weight:600;">ðŸ“¥ Download Protocol</a>',
                unsafe_allow_html=True,
            )

            # Interactive checklist
            st.subheader("âœ… Interactive Workbench Checklist")
            checklist = protocol.get("checklist", [])
            if checklist:
                for i, item in enumerate(checklist):
                    col1, col2 = st.columns([0.1, 0.9])
                    with col1:
                        st.checkbox("", key=f"checklist_{i}")
                    with col2:
                        cat_icon = {"reagent": "Ã°Å¸Â§Âª", "equipment": "Ã°Å¸â€Â¬", "software": "Ã°Å¸â€™Â»", "safety": "Ã¢Å¡Â Ã¯Â¸Â"}.get(
                            item.get("category", ""), "ðŸ“‹"
                        )
                        st.markdown(f"{cat_icon} **{item['item']}**")
                        if item.get("notes"):
                            st.caption(item["notes"])

    with tab3:
        protocol = st.session_state.get("_last_protocol")
        if not protocol:
            st.info("Transpile a protocol first.")
        else:
            st.subheader("Ã°Å¸â€™Â» Copyable Code & Commands")

            code_blocks = protocol.get("code_blocks", [])
            if code_blocks:
                for i, cb in enumerate(code_blocks):
                    lang = cb.get("language", "text")
                    with st.expander(f"Code Block {i1} [{lang}]", expanded=(i == 0)):
                        st.code(cb["code"], language=lang if lang != "unknown" else "text")
            else:
                st.info("No code blocks detected in the methodology text.")

            # Generate bash commands
            st.subheader("Ã°Å¸â€“Â¥Ã¯Â¸Â Generated Bash Commands")
            commands = transpiler.generate_bash_commands(protocol)
            bash_script = "\n".join(commands)
            st.code(bash_script, language="bash")

            import base64
            b64 = base64.b64encode(bash_script.encode()).decode()
            st.markdown(
                f'<a href="data:text/plain;base64,{b64}" download="commands.sh" '
                f'style="display:inline-block;padding:10px 20px;background:#059669;color:white;'
                f'border-radius:8px;text-decoration:none;font-weight:600;">ðŸ“¥ Download Bash Script</a>',
                unsafe_allow_html=True,
            )

            # Timer presets
            st.subheader("Ã¢ÂÂ±Ã¯Â¸Â Timer Presets")
            durations = protocol.get("durations", [])
            if durations:
                for d in durations:
                    st.markdown(f"Ã¢ÂÂ±Ã¯Â¸Â {d['value']}")
            else:
                st.info("No durations detected to create timer presets.")

