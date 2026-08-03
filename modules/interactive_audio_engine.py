
"""
Hands-Free 'Pause & Interrupt' Conversational Audio Engine
Upgrades audio briefings into an interactive, voice-controlled learning space.
Users can interrupt via voice or tap, ask clarifying questions, and resume.
"""
from __future__ import annotations

import json, re, time, threading
from datetime import datetime
from typing import Dict, List, Any, Optional, Callable


class InteractiveAudioEngine:
    """Interactive audio briefing with pause/interrupt/resume and voice commands."""

    def __init__(self):
        self.is_playing = False
        self.is_paused = False
        self.current_position = 0.0
        self.current_segment_index = 0
        self.segments: List[Dict[str, Any]] = []
        self.context: Dict[str, Any] = {}
        self.listeners: List[Callable] = []
        self.command_history: List[Dict] = []
        self._voice_active = False

    def register_listener(self, callback: Callable):
        self.listeners.append(callback)

    def _notify_listeners(self, event: str, data: Any = None):
        for cb in self.listeners:
            try: cb(event, data)
            except Exception: pass

    def load_briefing(self, briefing_text: str, paper_context: Optional[Dict] = None):
        paragraphs = [p.strip() for p in briefing_text.split("\n\n") if p.strip()]
        self.segments = [{"index": i, "text": para, "word_count": len(para.split()), "duration_estimate": len(para.split()) * 0.3} for i, para in enumerate(paragraphs)]
        self.context = {"paper": paper_context or {}, "total_segments": len(self.segments), "total_words": sum(s["word_count"] for s in self.segments), "loaded_at": datetime.now().strftime("%H:%M:%S")}
        self.current_segment_index = 0; self.current_position = 0.0
        self._notify_listeners("briefing_loaded", {"segments": len(self.segments)})

    def start_playback(self):
        self.is_playing = True; self.is_paused = False
        self._notify_listeners("playback_started", {"segment": self.current_segment_index})

    def pause_playback(self):
        self.is_paused = True
        self._notify_listeners("playback_paused", {"position": self.current_position})

    def resume_playback(self):
        self.is_paused = False
        self._notify_listeners("playback_resumed", {"segment": self.current_segment_index})

    def stop_playback(self):
        self.is_playing = False; self.is_paused = False; self.current_position = 0.0; self.current_segment_index = 0
        self._notify_listeners("playback_stopped", {})

    def skip_forward(self, segments: int = 1):
        self.current_segment_index = min(len(self.segments) - 1, self.current_segment_index  segments)
        self.current_position = 0.0
        self._notify_listeners("segments_skipped", {"new_index": self.current_segment_index, "direction": "forward"})

    def skip_backward(self, segments: int = 1):
        self.current_segment_index = max(0, self.current_segment_index - segments)
        self.current_position = 0.0
        self._notify_listeners("segments_skipped", {"new_index": self.current_segment_index, "direction": "backward"})

    def seek_to_segment(self, index: int):
        if 0 <= index < len(self.segments):
            self.current_segment_index = index; self.current_position = 0.0
            self._notify_listeners("seeked", {"segment": index})

    def process_voice_command(self, command_text: str) -> Dict[str, Any]:
        cmd_lower = command_text.lower().strip()
        response = {"command": command_text, "action": None, "response_text": "", "success": False}
        self.command_history.append({"timestamp": time.time(), "command": command_text, "parsed_at": datetime.now().strftime("%H:%M:%S")})

        if any(w in cmd_lower for w in ["pause", "stop", "wait", "hold up", "hold on"]):
            self.pause_playback()
            response.update({"action": "pause", "response_text": "â¸ï¸ Paused. Say 'resume' or 'continue' when ready.", "success": True})
        elif any(w in cmd_lower for w in ["resume", "continue", "play", "go on", "keep going"]):
            self.resume_playback() if self.is_paused else self.start_playback()
            response.update({"action": "resume", "response_text": "â–¶ï¸ Resuming.", "success": True})
        elif any(w in cmd_lower for w in ["back", "previous", "go back", "repeat"]):
            self.skip_backward(1)
            response.update({"action": "back", "response_text": "âª Previous segment.", "success": True})
        elif any(w in cmd_lower for w in ["next", "forward", "skip", "ahead"]):
            self.skip_forward(1)
            response.update({"action": "next", "response_text": "â© Next segment.", "success": True})
        elif any(w in cmd_lower for w in ["explain", "what does", "what is", "clarify", "tell me more"]):
            response.update(self._handle_explain_request(cmd_lower))
        elif any(w in cmd_lower for w in ["sample size", "how many", "participants", "n="]):
            response.update(self._handle_sample_size_query(cmd_lower))
        elif any(w in cmd_lower for w in ["methodology", "method", "how did they", "procedure"]):
            response.update(self._handle_methodology_query(cmd_lower))
        elif any(w in cmd_lower for w in ["result", "finding", "conclusion", "what did they find"]):
            response.update(self._handle_results_query(cmd_lower))
        elif any(w in cmd_lower for w in ["statistics", "p value", "effect size", "significance"]):
            response.update(self._handle_statistics_query(cmd_lower))
        elif re.search(r'go to (segment|part|section) (\d)', cmd_lower):
            m = re.search(r'(\d)', cmd_lower)
            if m:
                idx = int(m.group(1)) - 1
                if 0 <= idx < len(self.segments):
                    self.seek_to_segment(idx)
                    response.update({"action": "seek", "response_text": f"ðŸ“ Segment {idx1}.", "success": True})
                else:
                    response.update({"response_text": f"Only {len(self.segments)} segments available."})
        elif any(w in cmd_lower for w in ["summarize", "summary", "key points", "overview"]):
            response.update(self._handle_summary_request())
        elif any(w in cmd_lower for w in ["help", "what can i say", "commands"]):
            response.update({"action": "help", "response_text": self._get_help_text(), "success": True})
        else:
            response.update({"response_text": "Try: pause, resume, explain, summarize, or help.", "action": "unknown"})
        return response

    def _handle_explain_request(self, cmd: str) -> Dict:
        segment = self.segments[self.current_segment_index] if self.segments else None
        if segment:
            return {"action": "explain", "response_text": f"ðŸ“– Here's context on this section: {segment['text'][:300]}...", "success": True}
        return {"response_text": "No content loaded to explain.", "action": "explain"}

    def _handle_sample_size_query(self, cmd: str) -> Dict:
        paper = self.context.get("paper", {})
        n = paper.get("sample_size", paper.get("n", "not specified"))
        return {"action": "sample_size", "response_text": f" The study sample size is: {n}", "success": True}

    def _handle_methodology_query(self, cmd: str) -> Dict:
        paper = self.context.get("paper", {})
        method = paper.get("methodology", paper.get("method", "not specified in context"))
        return {"action": "methodology", "response_text": f"ðŸ”¬ Methodology: {method}", "success": True}

    def _handle_results_query(self, cmd: str) -> Dict:
        paper = self.context.get("paper", {})
        findings = paper.get("findings", paper.get("results", "not specified in context"))
        return {"action": "results", "response_text": f"ðŸ“ˆ Key findings: {findings}", "success": True}

    def _handle_statistics_query(self, cmd: str) -> Dict:
        paper = self.context.get("paper", {})
        stats = paper.get("statistics", paper.get("stats", "not specified"))
        return {"action": "statistics", "response_text": f"ðŸ“‰ Statistical details: {stats}", "success": True}

    def _handle_summary_request(self) -> Dict:
        if not self.segments:
            return {"response_text": "No content loaded.", "action": "summary"}
        total_words = sum(s["word_count"] for s in self.segments)
        first_seg = self.segments[0]["text"][:200] if self.segments else ""
        return {"action": "summary", "response_text": f"ðŸ“„ Briefing with {len(self.segments)} segments ({total_words} words). Starts with: {first_seg}...", "success": True}

    def _get_help_text(self) -> str:
        return """ðŸŽ¯ **Available Commands:**
â€¢ **Playback**: pause, resume, stop, next, back, go to segment [N]
â€¢ **Questions**: explain this, what does this mean, clarify
â€¢ **Paper Info**: sample size, methodology, results, statistics
â€¢ **Navigation**: summarize, overview, key points
â€¢ **Help**: help, commands, what can I say"""

    def get_current_segment(self) -> Optional[Dict]:
        if 0 <= self.current_segment_index < len(self.segments):
            return self.segments[self.current_segment_index]
        return None

    def get_progress(self) -> float:
        if not self.segments: return 0.0
        return (self.current_segment_index  1) / len(self.segments) * 100

    def get_state_summary(self) -> Dict:
        return {
            "is_playing": self.is_playing, "is_paused": self.is_paused,
            "current_segment": self.current_segment_index,
            "total_segments": len(self.segments),
            "progress_pct": self.get_progress(),
            "commands_processed": len(self.command_history),
        }


def render_interactive_audio_ui():
    """Render the Interactive Audio Engine UI."""
    import streamlit as st
    st.markdown("## ðŸŽ™ï¸ Interactive Audio Briefing Engine")
    st.markdown("*Voice-controlled research briefing with pause & interrupt*")

    if "audio_engine" not in st.session_state:
        st.session_state["audio_engine"] = InteractiveAudioEngine()
    engine = st.session_state["audio_engine"]

    tab1, tab2, tab3 = st.tabs(["ðŸŽ§ Player", "ðŸŽ¯ Voice Commands", "ðŸ“‹ History"])

    with tab1:
        st.subheader("ðŸŽ§ Audio Briefing Player")
        col1, col2 = st.columns([2, 1])
        with col1:
            briefing_text = st.text_area("Briefing text to narrate", height=150,
                placeholder="Paste research briefing content here...\n\nEach paragraph becomes a navigable segment.",
                key="audio_briefing_input")
        with col2:
            st.markdown("**Paper Context (optional)**")
            sample_size = st.text_input("Sample size", placeholder="N=150", key="audio_sample_size")
            methodology = st.text_input("Methodology", placeholder="RCT, double-blind", key="audio_method")
            findings = st.text_area("Key findings", height=60, placeholder="Main results...", key="audio_findings")

        if st.button("ðŸ“¥ Load Briefing", type="primary", use_container_width=True) and briefing_text:
            paper_ctx = {"sample_size": sample_size, "methodology": methodology, "findings": findings, "statistics": ""}
            engine.load_briefing(briefing_text, paper_ctx)
            st.success(f"âœ… Loaded {len(engine.segments)} segments")

        if engine.segments:
            st.markdown("### Controls")
            col1, col2, col3, col4, col5 = st.columns(5)
            with col1:
                if st.button("â®ï¸", use_container_width=True): engine.skip_backward(2); st.rerun()
            with col2:
                if st.button("âª", use_container_width=True): engine.skip_backward(1); st.rerun()
            with col3:
                if engine.is_paused:
                    if st.button("â–¶ï¸ Resume", use_container_width=True): engine.resume_playback(); st.rerun()
                else:
                    if st.button("â¸ï¸ Pause", use_container_width=True): engine.pause_playback(); st.rerun()
            with col4:
                if st.button("â©", use_container_width=True): engine.skip_forward(1); st.rerun()
            with col5:
                if st.button("â­ï¸", use_container_width=True): engine.skip_forward(2); st.rerun()

            st.markdown("### Current Segment")
            seg = engine.get_current_segment()
            if seg:
                st.info(f"**Segment {seg['index']1}/{len(engine.segments)}** ({seg['word_count']} words)")
                st.markdown(seg['text'])
                st.progress(engine.get_progress() / 100)
            else:
                st.info("No segment selected")

    with tab2:
        st.subheader("ðŸŽ¯ Voice & Text Commands")
        st.caption("Type a command or use voice input (if microphone is available)")
        command = st.text_input("Enter command", placeholder="e.g., pause, explain this, sample size...", key="audio_command")
        if st.button("ðŸŽ¤ Send Command", type="primary") and command:
            result = engine.process_voice_command(command)
            if result["success"]:
                st.success(result["response_text"])
            else:
                st.info(result["response_text"])
        st.markdown("### Available Commands")
        st.markdown(engine._get_help_text())

    with tab3:
        st.subheader("ðŸ“‹ Command History")
        if engine.command_history:
            for cmd in reversed(engine.command_history[-20:]):
                ts = datetime.fromtimestamp(cmd["timestamp"]).strftime("%H:%M:%S")
                st.text(f"[{ts}] {cmd['command']}")
        else:
            st.info("No commands processed yet")
        state = engine.get_state_summary()
        st.markdown("### Engine State")
        st.json(state)

