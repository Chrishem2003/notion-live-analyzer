import security_guard

"""
AI Co-Researcher & Automation Layer
Intelligent research assistant that processes meeting transcripts in real-time,
auto-detects action items, and generates live meeting notes appended to the project state.

Features:
  - Real-time speech-to-text transcript processing hook
  - Auto-detection of action items from conversation
  - Live meeting notes generation appended directly to project state
  - Research context integration with existing analysis modules
  - Semantic topic extraction and summarization
  - Sentiment and engagement analysis

Architecture:
  - Pipeline-based transcript processing with configurable stages
  - Rule-based  ML-light action item extraction
  - Context window management for coherent note generation
  - Integration hooks for existing modules (literature_engine, ai_analyzer, etc.)
"""
from __future__ import annotations

import hashlib
import json
import re
import time
import uuid
from collections import defaultdict
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any, Tuple, Callable, Set


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# ENUMS & CONSTANTS
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

class TranscriptSource(str, Enum):
    LIVE_SPEECH = "live_speech"              # Real-time microphone input
    AUDIO_FILE = "audio_file"                # Uploaded audio recording
    VIDEO_CALL = "video_call"                # WebRTC meeting audio
    TEXT_INPUT = "text_input"                # Manually typed/pasted text
    IMPORTED = "imported"                    # Imported from external source


class NoteCategory(str, Enum):
    ACTION_ITEM = "action_item"
    DECISION = "decision"
    QUESTION = "question"
    FINDING = "finding"
    HYPOTHESIS = "hypothesis"
    METHODOLOGY = "methodology"
    REFERENCE = "reference"
    FOLLOW_UP = "follow_up"
    GENERAL = "general"


class ActionItemPriority(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ActionItemStatus(str, Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    BLOCKED = "blocked"
    CANCELLED = "cancelled"


# Confidence thresholds
ACTION_ITEM_CONFIDENCE_THRESHOLD = 0.65
TOPIC_EXTRACTION_THRESHOLD = 0.5
SENTENCE_SIMILARITY_THRESHOLD = 0.7

# Processing constants
MAX_TRANSCRIPT_HISTORY = 10000  # max stored transcript segments
NOTE_CONTEXT_WINDOW = 5  # number of transcript segments to include in note context
SUMMARIZATION_INTERVAL = 50  # generate summary every N transcript segments


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# DATA MODELS
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

class TranscriptSegment:
    """
    A single segment of transcribed speech.
    Represents one utterance/sentence from a participant.
    """

    def __init__(self, text: str, speaker_id: str, speaker_name: str,
                 source: TranscriptSource = TranscriptSource.LIVE_SPEECH,
                 timestamp: Optional[float] = None,
                 language: str = "en"):
        self.id = f"ts_{uuid.uuid4().hex[:12]}"
        self.text = text.strip()
        self.speaker_id = speaker_id
        self.speaker_name = speaker_name
        self.source = source
        self.timestamp = timestamp or time.time()
        self.language = language
        self.word_count = len(text.split())
        self.duration_estimate = self.word_count * 0.3  # ~300ms per word

        # Processing results
        self.processed_topics: List[str] = []
        self.sentiment_score: Optional[float] = None  # -1 to 1
        self.urgency_score: Optional[float] = None    # 0 to 1
        self.is_question = False
        self.has_action_item = False
        self.extracted_action_items: List[ActionItem] = []

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "id": self.id,
            "text": self.text,
            "speaker_id": self.speaker_id,
            "speaker_name": self.speaker_name,
            "source": self.source.value,
            "timestamp": self.timestamp,
            "language": self.language,
            "word_count": self.word_count,
            "processed_topics": self.processed_topics,
            "sentiment_score": self.sentiment_score,
            "urgency_score": self.urgency_score,
            "is_question": self.is_question,
            "has_action_item": self.has_action_item,
        }


class ActionItem:
    """
    An action item extracted from a meeting transcript.
    Tracks assignment, priority, status, and dependencies.
    """

    def __init__(self, description: str, extracted_by: str,
                 source_segment_id: str,
                 assignee_id: Optional[str] = None,
                 assignee_name: Optional[str] = None,
                 priority: ActionItemPriority = ActionItemPriority.MEDIUM,
                 due_by: Optional[float] = None):
        self.id = f"ai_{uuid.uuid4().hex[:12]}"
        self.description = description
        self.extracted_by = extracted_by
        self.extracted_at = time.time()
        self.source_segment_id = source_segment_id

        # Assignment
        self.assignee_id = assignee_id
        self.assignee_name = assignee_name
        self.status = ActionItemStatus.OPEN

        # Priority & timing
        self.priority = priority
        self.created_at = time.time()
        self.due_by = due_by
        self.completed_at: Optional[float] = None

        # Context
        self.context_notes: List[str] = []
        self.dependent_item_ids: List[str] = []
        self.tags: List[str] = []
        self.project_id: Optional[str] = None

        # ML confidence
        self.confidence: float = 0.0
        self.extraction_method: str = "rule_based"  # rule_based, ml, manual

    def assign(self, user_id: str, user_name: str):
        """Assign this action item to a user."""
        self.assignee_id = user_id
        self.assignee_name = user_name
        self.status = ActionItemStatus.OPEN

    def complete(self):
        """Mark this action item as completed."""
        self.status = ActionItemStatus.COMPLETED
        self.completed_at = time.time()

    def block(self, reason: str = ""):
        """Mark this action item as blocked."""
        self.status = ActionItemStatus.BLOCKED
        if reason:
            self.context_notes.append(f"Blocked: {reason}")

    def add_dependency(self, action_item_id: str):
        """Add a dependency on another action item."""
        if action_item_id not in self.dependent_item_ids:
            self.dependent_item_ids.append(action_item_id)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "id": self.id,
            "description": self.description,
            "extracted_by": self.extracted_by,
            "extracted_at": self.extracted_at,
            "assignee_id": self.assignee_id,
            "assignee_name": self.assignee_name,
            "status": self.status.value,
            "priority": self.priority.value,
            "created_at": self.created_at,
            "due_by": self.due_by,
            "completed_at": self.completed_at,
            "confidence": self.confidence,
            "tags": self.tags,
            "dependent_items": self.dependent_item_ids,
        }


class MeetingNote:
    """
    A structured meeting note generated from transcript analysis.
    Contains extracted decisions, findings, questions, and follow-ups.
    """

    def __init__(self, title: str, content: str, category: NoteCategory,
                 generated_by: str,
                 source_segment_ids: Optional[List[str]] = None):
        self.id = f"mn_{uuid.uuid4().hex[:12]}"
        self.title = title
        self.content = content
        self.category = category
        self.generated_by = generated_by
        self.generated_at = time.time()

        # Source attribution
        self.source_segment_ids = source_segment_ids or []

        # Metadata
        self.tags: List[str] = []
        self.references: List[str] = []
        self.related_note_ids: List[str] = []
        self.is_pinned = False
        self.is_resolved = False

        # Project integration
        self.project_id: Optional[str] = None
        self.page_id: Optional[str] = None  # Notion page ID if synced

    def resolve(self):
        """Mark this note as resolved."""
        self.is_resolved = True

    def pin(self):
        """Pin this note for prominence."""
        self.is_pinned = True

    def unpin(self):
        """Unpin this note."""
        self.is_pinned = False

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "id": self.id,
            "title": self.title,
            "content": self.content,
            "category": self.category.value,
            "generated_by": self.generated_by,
            "generated_at": self.generated_at,
            "tags": self.tags,
            "is_pinned": self.is_pinned,
            "is_resolved": self.is_resolved,
            "source_segments": self.source_segment_ids[:5],
        }


class ResearchContext:
    """
    Research context that integrates with existing analysis modules.
    Provides hooks into literature_engine, ai_analyzer, and other modules
    for enriched meeting intelligence.
    """

    def __init__(self, project_id: str):
        self.project_id = project_id
        self.active_hypotheses: List[Dict[str, Any]] = []
        self.recent_findings: List[Dict[str, Any]] = []
        self.relevant_literature: List[Dict[str, Any]] = []
        self.methodology_notes: List[str] = []
        self.statistical_notes: List[str] = []

        # Integration hooks (set by external modules)
        self._literature_hook: Optional[Callable] = None
        self._hypothesis_hook: Optional[Callable] = None
        self._analysis_hook: Optional[Callable] = None

    def register_literature_hook(self, hook: Callable):
        """Register a hook to the literature engine."""
        self._literature_hook = hook

    def register_hypothesis_hook(self, hook: Callable):
        """Register a hook to the hypothesis generator."""
        self._hypothesis_hook = hook

    def register_analysis_hook(self, hook: Callable):
        """Register a hook to the AI analysis engine."""
        self._analysis_hook = hook

    def query_literature(self, topic: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """Query the literature engine for relevant papers."""
        if self._literature_hook:
            try:
                results = self._literature_hook(topic=topic, max_results=max_results)
                self.relevant_literature.extend(results[:max_results])
                return results[:max_results]
            except Exception:
                pass
        return []

    def query_hypotheses(self, finding: str) -> List[Dict[str, Any]]:
        """Query the hypothesis generator for relevant hypotheses."""
        if self._hypothesis_hook:
            try:
                results = self._hypothesis_hook(finding=finding)
                self.active_hypotheses.extend(results)
                return results
            except Exception:
                pass
        return []

    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of the research context."""
        return {
            "project_id": self.project_id,
            "active_hypotheses": len(self.active_hypotheses),
            "recent_findings": len(self.recent_findings),
            "relevant_literature": len(self.relevant_literature),
            "methodology_notes": len(self.methodology_notes),
            "statistical_notes": len(self.statistical_notes),
            "integration_hooks": {
                "literature": self._literature_hook is not None,
                "hypothesis": self._hypothesis_hook is not None,
                "analysis": self._analysis_hook is not None,
            }
        }


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# TRANSCRIPT PROCESSOR
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

class TranscriptProcessor:
    """
    Real-time speech-to-text transcript processing pipeline.
    Stages:
      1. Ingest: Receive raw transcript segments from STT engine
      2. Clean: Normalize text, remove filler words, fix punctuation
      3. Analyze: Extract topics, sentiment, urgency, questions
      4. Extract: Detect action items and key information
      5. Summarize: Generate periodic summaries
    """

    def __init__(self):
        self.segments: List[TranscriptSegment] = []
        self.speaker_sessions: Dict[str, Dict[str, Any]] = {}
        self.is_processing = False
        self.processing_lag = 0.0  # seconds behind real-time

        # Processing state
        self._last_summary_index = 0
        self._accumulated_text = ""
        self._topic_frequencies: Dict[str, int] = defaultdict(int)

        # Filler words to remove
        self._filler_words = {
            "um", "uh", "ah", "er", "like", "you know", "actually",
            "basically", "literally", "sort of", "kind of", "i mean",
        }

        # Action item trigger patterns
        self._action_item_patterns = [
            # Direct assignments
            r"(?:can|could|will|shall)\s(?:you|we|someone)\s(?:please\s)?(\w[\w\s])",
            r"(?:i\'?ll|we\'?ll)\s(\w[\w\s])",
            r"(?:assigned?|responsible for|tasked with)\s(\w[\w\s])",
            r"(?:need to|have to|must|should)\s(\w[\w\s])",
            # Follow-up triggers
            r"(?:follow up|check|review|update|prepare|create|write|submit|send)\s(?:on|the|a|an)?\s*(\w[\w\s])",
            r"(?:next steps?|action items?|to-do|todo|todos?):?\s*(.)$",
            # Decision indicators
            r"(?:decided?|agreed?|consensus|concluded?)\s(?:that|to|on)?\s*(\w[\w\s])",
            r"let\s(\w[\w\s])",
        ]

    def ingest(self, text: str, speaker_id: str, speaker_name: str,
               source: TranscriptSource = TranscriptSource.LIVE_SPEECH,
               language: str = "en") -> TranscriptSegment:
        """
        Ingest a new transcript segment from the STT engine.
        Returns the processed segment.
        """
        # Create segment
        segment = TranscriptSegment(text, speaker_id, speaker_name, source, language=language)
        self.segments.append(segment)

        # Update speaker session
        if speaker_id not in self.speaker_sessions:
            self.speaker_sessions[speaker_id] = {
                "name": speaker_name,
                "segment_count": 0,
                "total_words": 0,
                "first_seen": time.time(),
                "last_seen": time.time(),
            }
        session = self.speaker_sessions[speaker_id]
        session["segment_count"] = 1
        session["total_words"] = segment.word_count
        session["last_seen"] = time.time()

        # Process the segment (async in production)
        self._process_segment(segment)

        # Trim history
        if len(self.segments) > MAX_TRANSCRIPT_HISTORY:
            self.segments = self.segments[-MAX_TRANSCRIPT_HISTORY:]

        return segment

    def _process_segment(self, segment: TranscriptSegment):
        """Process a single transcript segment through the pipeline."""
        start_time = time.time()

        # Stage 1: Clean text
        cleaned_text = self._clean_text(segment.text)
        segment.text = cleaned_text

        # Stage 2: Analyze
        segment.is_question = self._detect_question(cleaned_text)
        segment.sentiment_score = self._analyze_sentiment(cleaned_text)
        segment.urgency_score = self._analyze_urgency(cleaned_text)
        segment.processed_topics = self._extract_topics(cleaned_text)

        # Update topic frequencies
        for topic in segment.processed_topics:
            self._topic_frequencies[topic] = 1

        # Stage 3: Extract action items
        action_items = self._extract_action_items(cleaned_text, segment.id)
        if action_items:
            segment.has_action_item = True
            segment.extracted_action_items = action_items

        # Accumulate for summary
        self._accumulated_text = " "  cleaned_text

        # Check if we should generate a summary
        if len(self.segments) - self._last_summary_index >= SUMMARIZATION_INTERVAL:
            segment.processed_topics.append("__summary_point__")

        self.processing_lag = time.time() - start_time

    def _clean_text(self, text: str) -> str:
        """Clean and normalize text."""
        # Remove filler words (case insensitive)
        words = text.split()
        cleaned = []
        for w in words:
            if w.lower() not in self._filler_words:
                cleaned.append(w)

        text = " ".join(cleaned)

        # Normalize whitespace
        text = re.sub(r'\s', ' ', text).strip()

        # Fix common punctuation issues
        text = re.sub(r'\s([.,!?;:])', r'\1', text)
        text = re.sub(r'\.{2,}', '.', text)

        # Capitalize first letter
        if text and text[0].islower():
            text = text[0].upper()  text[1:]

        return text

    def _detect_question(self, text: str) -> bool:
        """Detect if a segment is a question."""
        # Ends with question mark
        if text.rstrip().endswith("?"):
            return True

        # Starts with question words
        question_starts = {
            "what", "why", "how", "when", "where", "who", "which",
            "whose", "whom", "is", "are", "was", "were", "do", "does",
            "did", "can", "could", "will", "would", "shall", "should",
            "has", "have", "had", "doesn't", "don't", "didn't", "aren't",
            "isn't", "wasn't", "weren't", "haven't", "hasn't", "hadn't",
            "can't", "couldn't", "won't", "wouldn't", "shouldn't",
        }
        first_word = text.split()[0].lower().rstrip(",") if text.split() else ""
        return first_word in question_starts

    def _analyze_sentiment(self, text: str) -> Optional[float]:
        """
        Analyze the sentiment of a text segment.
        Returns a score from -1 (negative) to 1 (positive).

        Uses a lightweight lexicon-based approach.
        """
        # Positive word list (abbreviated)
        positive_words = {
            "great", "excellent", "good", "amazing", "wonderful", "fantastic",
            "outstanding", "brilliant", "impressive", "perfect", "beautiful",
            "love", "happy", "pleased", "delighted", "satisfied", "confident",
            "encouraging", "promising", "breakthrough", "success", "successful",
            "beneficial", "helpful", "useful", "valuable", "significant",
            "remarkable", "notable", "positive", "optimistic", "hope",
            "progress", "improvement", "enhanced", "strengthened",
        }

        # Negative word list (abbreviated)
        negative_words = {
            "bad", "terrible", "awful", "poor", "horrible", "dreadful",
            "hate", "angry", "frustrated", "disappointed", "unsatisfied",
            "worse", "worst", "failure", "failed", "problem", "problems",
            "difficult", "hard", "impossible", "unlikely", "concern",
            "concerned", "worried", "anxious", "stressful", "tension",
            "conflict", "disagreement", "dispute", "negative", "pessimistic",
            "doubt", "uncertain", "unclear", "ambiguous", "lacking",
            "insufficient", "inadequate", "limited", "restricted",
        }

        words = set(w.lower().rstrip(".,!?;:") for w in text.split())
        pos_count = sum(1 for w in words if w in positive_words)
        neg_count = sum(1 for w in words if w in negative_words)
        total = pos_count  neg_count

        if total == 0:
            return 0.0

        return (pos_count - neg_count) / total

    def _analyze_urgency(self, text: str) -> float:
        """
        Analyze the urgency level of a text segment.
        Returns a score from 0 (not urgent) to 1 (critical).
        """
        urgency_indicators = {
            "urgent": 1.0, "critical": 1.0, "immediately": 0.95,
            "asap": 0.95, "emergency": 1.0, "deadline": 0.8,
            "overdue": 0.9, "blocker": 0.85, "blocking": 0.85,
            "time-sensitive": 0.9, "priority": 0.7, "crucial": 0.85,
            "vital": 0.8, "essential": 0.7, "must": 0.6,
            "important": 0.5, "soon": 0.4, "today": 0.6,
            "tomorrow": 0.5, "this week": 0.4, "quickly": 0.6,
            "rush": 0.8, "hurry": 0.7, "fast": 0.5,
        }

        text_lower = text.lower()
        max_urgency = 0.0

        for indicator, score in urgency_indicators.items():
            if indicator in text_lower:
                max_urgency = max(max_urgency, score)

        return max_urgency

    def _extract_topics(self, text: str) -> List[str]:
        """
        Extract key topics from text using keyword matching.
        In production, this would use NLP (TF-IDF, topic modeling).
        """
        # Research domain keywords
        domain_keywords = {
            "methodology": {"method", "methodology", "procedure", "protocol",
                            "approach", "technique", "analysis", "measurement"},
            "statistics": {"statistic", "p-value", "effect size", "correlation",
                           "regression", "significance", "variance", "distribution"},
            "data": {"data", "dataset", "sample", "observation", "variable",
                     "feature", "collection", "quality"},
            "hypothesis": {"hypothesis", "theory", "prediction", "assumption",
                           "proposition", "conjecture", "postulate"},
            "results": {"result", "finding", "outcome", "conclusion",
                        "discovery", "observation", "evidence"},
            "literature": {"paper", "publication", "study", "research",
                           "article", "journal", "reference", "citation"},
            "implementation": {"implement", "deploy", "build", "develop",
                               "code", "pipeline", "workflow", "system"},
            "collaboration": {"collaborate", "team", "meeting", "discuss",
                              "present", "review", "feedback", "share"},
        }

        text_lower = text.lower()
        found_topics = []

        for topic, keywords in domain_keywords.items():
            for keyword in keywords:
                if keyword in text_lower:
                    found_topics.append(topic)
                    break

        # Extract potential named entities (capitalized words, excluding start of sentence)
        words = text.split()
        for i, w in enumerate(words):
            if i > 0 and w[0].isupper() and len(w) > 2:
                cleaned = w.strip(".,!?;:()[]{}")
                if cleaned and cleaned.lower() not in self._filler_words:
                    found_topics.append(cleaned)

        # Deduplicate and limit
        seen = set()
        unique_topics = []
        for t in found_topics:
            if t not in seen:
                seen.add(t)
                unique_topics.append(t)

        return unique_topics[:5]  # Max 5 topics per segment

    def _extract_action_items(self, text: str, segment_id: str) -> List[ActionItem]:
        """
        Extract action items from text using pattern matching.
        Returns a list of potential ActionItem objects.
        """
        items = []

        for pattern in self._action_item_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                # Extract the actionable part
                action_text = match.group(0).strip()

                # Try to find an assignee
                assignee_id = None
                assignee_name = None
                assignee_match = re.search(
                    r'(?:assign\s(?:it\s)?to\s|for\s)(@?\w[\w\s])',
                    text, re.IGNORECASE
                )
                if assignee_match:
                    assignee_name = assignee_match.group(1).strip()

                # Determine priority based on urgency indicators
                urgency = self._analyze_urgency(action_text)
                if urgency >= 0.8:
                    priority = ActionItemPriority.CRITICAL
                elif urgency >= 0.6:
                    priority = ActionItemPriority.HIGH
                elif urgency >= 0.3:
                    priority = ActionItemPriority.MEDIUM
                else:
                    priority = ActionItemPriority.LOW

                # Create action item
                item = ActionItem(
                    description=action_text,
                    extracted_by="ai_researcher",
                    source_segment_id=segment_id,
                    assignee_id=assignee_id,
                    assignee_name=assignee_name,
                    priority=priority,
                )
                extractor = ActionItemDetector()
                item.confidence = extractor.calculate_confidence(action_text, text)
                item.extraction_method = "rule_based"

                if item.confidence >= ACTION_ITEM_CONFIDENCE_THRESHOLD:
                    items.append(item)

        # Deduplicate by description similarity
        unique_items = []
        for item in items:
            is_duplicate = False
            for existing in unique_items:
                if self._text_similarity(item.description, existing.description) > 0.8:
                    is_duplicate = True
                    break
            if not is_duplicate:
                unique_items.append(item)

        return unique_items[:3]  # Max 3 action items per segment

    def _text_similarity(self, text1: str, text2: str) -> float:
        """
        Calculate text similarity using Jaccard similarity on word sets.
        """
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())

        if not words1 or not words2:
            return 0.0

        intersection = words1.intersection(words2)
        union = words1.union(words2)

        return len(intersection) / len(union)

    def get_recent_segments(self, count: int = 10) -> List[TranscriptSegment]:
        """Get the most recent transcript segments."""
        return self.segments[-count:] if self.segments else []

    def get_speaker_statistics(self) -> Dict[str, Dict[str, Any]]:
        """Get speaking statistics for all participants."""
        stats = {}
        for sid, session in self.speaker_sessions.items():
            stats[sid] = {
                "name": session["name"],
                "segments": session["segment_count"],
                "total_words": session["total_words"],
                "participation_pct": 0.0,  # Calculated below
                "last_active": session["last_seen"],
            }

        total_segments = sum(s["segment_count"] for s in self.speaker_sessions.values())
        if total_segments > 0:
            for sid in stats:
                stats[sid]["participation_pct"] = round(
                    stats[sid]["segments"] / total_segments * 100, 1
                )

        return stats

    def get_top_topics(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get the most frequently discussed topics."""
        sorted_topics = sorted(
            self._topic_frequencies.items(),
            key=lambda x: x[1],
            reverse=True,
        )
        return [
            {"topic": topic, "frequency": count}
            for topic, count in sorted_topics[:limit]
        ]

    def generate_summary(self) -> str:
        """
        Generate a summary of the conversation so far.
        In production, this would use an LLM for abstractive summarization.
        """
        total_segments = len(self.segments)
        total_words = sum(s.word_count for s in self.segments)
        top_topics = self.get_top_topics(5)
        speaker_stats = self.get_speaker_statistics()
        active_speakers = [s for s in speaker_stats.values() if s["segments"] > 0]

        summary = (
            f" **Meeting Summary**\n\n"
            f"**Overview:** {total_segments} segments Â· {total_words} words Â· "
            f"{len(active_speakers)} active speakers\n\n"
        )

        if top_topics:
            summary = "**Key Topics:**\n"
            for t in top_topics[:5]:
                summary = f"  â€¢ {t['topic']} ({t['frequency']} mentions)\n"

        if active_speakers:
            summary = "\n**Speaker Participation:**\n"
            for s in sorted(active_speakers, key=lambda x: x["segments"], reverse=True)[:5]:
                summary = f"  â€¢ {s['name']}: {s['segments']} segments ({s['participation_pct']}%)\n"

        return summary


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# ACTION ITEM DETECTOR
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

class ActionItemDetector:
    """
    Dedicated action item detection and confidence calculation.
    Uses a combination of pattern matching, keyword analysis,
    and contextual heuristics to identify and score action items.
    """

    def __init__(self):
        # High-confidence patterns (direct assignments/commitments)
        self._direct_patterns = [
            r"(?:i\'?ll|we\'?ll)\s(\w[\w\s,;])",
            r"(?:can|will)\syou\s(\w[\w\s,;])",
            r"please\s(\w[\w\s,;])",
            r"your\s(?:task|action|responsibility)\s(?:is|:)\s*(\w[\w\s,;])",
        ]

        # Medium-confidence patterns (suggestions/needs)
        self._suggestion_patterns = [
            r"(?:we\s)?(?:should|need to|have to|must)\s(\w[\w\s,;])",
            r"(?:next steps?|action items?):?\s*(.)",
            r"(?:don\'t|do not)\sforget\sto\s(\w[\w\s,;])",
            r"remind\s(?:me|us|everyone)\sto\s(\w[\w\s,;])",
        ]

        # Low-confidence patterns (general obligations)
        self._obligation_patterns = [
            r"(?:it\'?s\s)?(?:important|crucial|essential|vital)\s(?:that\s)?(?:we|you)\s(\w[\w\s,;])",
            r"(?:make\ssure|ensure|verify|confirm)\s(?:that\s)?(\w[\w\s,;])",
            r"(?:follow up|check back|update)\s(?:on|with)\s(\w[\w\s,;])",
        ]

    def extract(self, text: str, segment_id: str) -> List[ActionItem]:
        """
        Extract action items from text with confidence scoring.
        """
        items = []

        # Check direct patterns (high confidence)
        for pattern in self._direct_patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                action_text = match.group(0).strip()
                item = ActionItem(
                    description=action_text,
                    extracted_by="action_detector",
                    source_segment_id=segment_id,
                    priority=ActionItemPriority.HIGH,
                )
                item.confidence = 0.85  (hash(action_text) % 10) / 100  # 0.85-0.95
                item.extraction_method = "pattern_direct"
                items.append(item)

        # Check suggestion patterns (medium confidence)
        for pattern in self._suggestion_patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                action_text = match.group(0).strip()
                # Check if already extracted
                if not any(self._text_similarity(item.description, action_text) > 0.7
                          for item in items):
                    item = ActionItem(
                        description=action_text,
                        extracted_by="action_detector",
                        source_segment_id=segment_id,
                        priority=ActionItemPriority.MEDIUM,
                    )
                    item.confidence = 0.65  (hash(action_text) % 15) / 100  # 0.65-0.80
                    item.extraction_method = "pattern_suggestion"
                    items.append(item)

        # Check obligation patterns (low confidence)
        for pattern in self._obligation_patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                action_text = match.group(0).strip()
                if not any(self._text_similarity(item.description, action_text) > 0.7
                          for item in items):
                    item = ActionItem(
                        description=action_text,
                        extracted_by="action_detector",
                        source_segment_id=segment_id,
                        priority=ActionItemPriority.LOW,
                    )
                    item.confidence = 0.45  (hash(action_text) % 15) / 100  # 0.45-0.60
                    item.extraction_method = "pattern_obligation"
                    items.append(item)

        return items

    def calculate_confidence(self, action_text: str, context: str) -> float:
        """
        Calculate confidence score for an action item extraction.
        Combines pattern match quality with contextual indicators.
        """
        confidence = 0.5  # Base

        # Length bonus (longer, more specific action items are more reliable)
        word_count = len(action_text.split())
        if word_count > 8:
            confidence = 0.1
        elif word_count > 5:
            confidence = 0.05

        # Contains a verb (action-oriented)
        verb_indicators = {"create", "update", "review", "submit", "send",
                           "prepare", "build", "fix", "check", "implement"}
        if any(v in action_text.lower() for v in verb_indicators):
            confidence = 0.1

        # Has an assignee mention
        if re.search(r'@?\w', action_text):
            confidence = 0.1

        # Context has urgency
        urgency = self._analyze_urgency_simple(context)
        confidence = urgency * 0.1

        # Contains time reference
        time_refs = {"by", "before", "after", "until", "within", "tomorrow",
                     "today", "next week", "by end of", "deadline"}
        if any(ref in action_text.lower() for ref in time_refs):
            confidence = 0.05

        return min(1.0, confidence)

    def _text_similarity(self, text1: str, text2: str) -> float:
        """Jaccard similarity on word sets."""
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        if not words1 or not words2:
            return 0.0
        return len(words1.intersection(words2)) / len(words1.union(words2))

    def _analyze_urgency_simple(self, text: str) -> float:
        """Simple urgency analysis for confidence boost."""
        urgency_words = {"urgent": 1.0, "asap": 0.9, "critical": 1.0,
                        "important": 0.6, "soon": 0.4, "deadline": 0.8}
        text_lower = text.lower()
        for word, score in urgency_words.items():
            if word in text_lower:
                return score
        return 0.0


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# AI RESEARCHER  Main Engine
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

class AIResearcher:
    """
    AI Co-Researcher that processes meeting transcripts in real-time,
    extracts action items and decisions, generates structured meeting notes,
    and integrates with existing research modules.

    Features:
      - Real-time transcript processing pipeline
      - Action item detection with confidence scoring
      - Automatic meeting note generation
      - Topic extraction and tracking
      - Speaker participation analytics
      - Integration with literature engine and hypothesis generator
      - Live note streaming to project state
    """

    def __init__(self, project_id: str, researcher_id: str):
        self.project_id = project_id
        self.researcher_id = researcher_id
        self.transcript_processor = TranscriptProcessor()
        self.action_detector = ActionItemDetector()

        # Research context (links to other modules)
        self.research_context = ResearchContext(project_id)

        # Generated notes
        self.notes: Dict[str, MeetingNote] = {}
        self.action_items: Dict[str, ActionItem] = {}
        self.pinned_notes: List[str] = []

        # Meeting metadata
        self.meeting_title: Optional[str] = None
        self.meeting_started_at: Optional[float] = None
        self.meeting_ended_at: Optional[float] = None
        self.is_recording = False
        self.participants: Set[str] = set()

        # Summary state
        self._last_summary_time = time.time()
        self._summary_count = 0

        # Event system
        self._listeners: Dict[str, List[Callable]] = {
            "transcript_ingested": [],
            "action_item_detected": [],
            "note_generated": [],
            "summary_generated": [],
            "meeting_started": [],
            "meeting_ended": [],
            "research_context_updated": [],
        }

    def on(self, event: str, callback: Callable):
        """Register an event listener."""
        if event in self._listeners:
            self._listeners[event].append(callback)

    def _emit(self, event: str, data: Any = None):
        """Emit an event to listeners."""
        for cb in self._listeners.get(event, []):
            try:
                cb(data)
            except Exception:
                pass

    # â”€â”€ Meeting Lifecycle â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def start_meeting(self, title: str = "Research Meeting"):
        """Start a new research meeting session."""
        self.meeting_title = title
        self.meeting_started_at = time.time()
        self.is_recording = True
        self._emit("meeting_started", {"title": title})

    def end_meeting(self) -> Dict[str, Any]:
        """End the current meeting and generate final summary."""
        self.is_recording = False
        self.meeting_ended_at = time.time()

        duration = 0
        if self.meeting_started_at:
            duration = self.meeting_ended_at - self.meeting_started_at

        # Generate final summary
        summary = self.transcript_processor.generate_summary()

        # Create final meeting note
        final_note = MeetingNote(
            title=f"Meeting Summary: {self.meeting_title or 'Untitled'}",
            content=summary,
            category=NoteCategory.GENERAL,
            generated_by=self.researcher_id,
        )
        self.notes[final_note.id] = final_note

        self._emit("meeting_ended", {
            "duration": duration,
            "total_segments": len(self.transcript_processor.segments),
            "total_notes": len(self.notes),
            "total_action_items": len(self.action_items),
        })

        return {
            "meeting_title": self.meeting_title,
            "duration_seconds": duration,
            "duration_display": f"{int(duration // 60)}m {int(duration % 60)}s",
            "total_segments": len(self.transcript_processor.segments),
            "summary": summary,
        }

    def add_participant(self, user_id: str, display_name: str):
        """Add a participant to the meeting."""
        self.participants.add(user_id)
        if user_id not in self.transcript_processor.speaker_sessions:
            self.transcript_processor.speaker_sessions[user_id] = {
                "name": display_name,
                "segment_count": 0,
                "total_words": 0,
                "first_seen": time.time(),
                "last_seen": time.time(),
            }

    # â”€â”€ Transcript Processing â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def ingest_transcript(self, text: str, speaker_id: str, speaker_name: str,
                          source: TranscriptSource = TranscriptSource.LIVE_SPEECH,
                          language: str = "en") -> Optional[TranscriptSegment]:
        """
        Ingest and process a new transcript segment.
        This is the main entry point for real-time STT integration.
        """
        if not self.is_recording:
            return None

        # Ensure speaker is tracked
        self.add_participant(speaker_id, speaker_name)

        # Process through pipeline
        segment = self.transcript_processor.ingest(
            text, speaker_id, speaker_name, source, language
        )

        self._emit("transcript_ingested", segment.to_dict())

        # Check for action items
        if segment.has_action_item:
            for action_item in segment.extracted_action_items:
                action_item.project_id = self.project_id
                self.action_items[action_item.id] = action_item
                self._emit("action_item_detected", action_item.to_dict())

                # Generate a note for this action item
                self._generate_note_from_action(action_item, segment)

        # Generate periodic summary
        if segment.processed_topics and "__summary_point__" in segment.processed_topics:
            self._generate_periodic_summary()

        return segment

    # â”€â”€ Note Generation â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def _generate_note_from_action(self, action_item: ActionItem,
                                    segment: TranscriptSegment) -> MeetingNote:
        """Generate a structured meeting note from an action item."""
        priority_icon = {
            ActionItemPriority.CRITICAL: "ðŸ”´",
            ActionItemPriority.HIGH: "ðŸŸ ",
            ActionItemPriority.MEDIUM: "ðŸŸ¡",
            ActionItemPriority.LOW: "ðŸŸ¢",
        }.get(action_item.priority, "âšª")

        assignee = f" â†’ @{action_item.assignee_name}" if action_item.assignee_name else ""

        content = (
            f"**Action Item** {priority_icon}\n\n"
            f"**{action_item.description}**{assignee}\n\n"
            f"Priority: {action_item.priority.value} | "
            f"Confidence: {action_item.confidence:.0%}\n"
            f"Status: {action_item.status.value}\n"
        )

        note = MeetingNote(
            title=f"Action: {action_item.description[:60]}{'...' if len(action_item.description) > 60 else ''}",
            content=content,
            category=NoteCategory.ACTION_ITEM,
            generated_by=self.researcher_id,
            source_segment_ids=[action_item.source_segment_id],
        )
        note.tags = ["action_item"]  action_item.tags

        self.notes[note.id] = note
        self._emit("note_generated", note.to_dict())
        return note

    def generate_note(self, title: str, content: str,
                       category: NoteCategory = NoteCategory.GENERAL,
                       tags: Optional[List[str]] = None) -> MeetingNote:
        """Manually generate a meeting note."""
        note = MeetingNote(
            title=title,
            content=content,
            category=category,
            generated_by=self.researcher_id,
        )
        note.tags = tags or []
        self.notes[note.id] = note
        self._emit("note_generated", note.to_dict())
        return note

    def _generate_periodic_summary(self):
        """Generate a periodic summary of the meeting."""
        self._summary_count = 1
        summary = self.transcript_processor.generate_summary()

        note = MeetingNote(
            title=f"â±ï¸ Progress Update #{self._summary_count}",
            content=summary,
            category=NoteCategory.GENERAL,
            generated_by=self.researcher_id,
        )
        note.tags = ["summary", "periodic"]
        self.notes[note.id] = note

        self._emit("summary_generated", note.to_dict())

    # â”€â”€ Query Methods â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def get_open_action_items(self) -> List[ActionItem]:
        """Get all open/in-progress action items."""
        return [
            item for item in self.action_items.values()
            if item.status in (ActionItemStatus.OPEN, ActionItemStatus.IN_PROGRESS)
        ]

    def get_notes_by_category(self, category: NoteCategory) -> List[MeetingNote]:
        """Get all notes of a specific category."""
        return [
            note for note in self.notes.values()
            if note.category == category and not note.is_resolved
        ]

    def get_pinned_notes(self) -> List[MeetingNote]:
        """Get all pinned notes."""
        return [
            self.notes[note_id] for note_id in self.pinned_notes
            if note_id in self.notes
        ]

    def get_meeting_state(self) -> Dict[str, Any]:
        """Get the full meeting state."""
        duration = 0
        if self.meeting_started_at:
            end = self.meeting_ended_at or time.time()
            duration = end - self.meeting_started_at

        return {
            "is_recording": self.is_recording,
            "meeting_title": self.meeting_title,
            "duration": duration,
            "duration_display": f"{int(duration // 60)}m {int(duration % 60)}s",
            "participants": len(self.participants),
            "segments_processed": len(self.transcript_processor.segments),
            "total_notes": len(self.notes),
            "open_action_items": len(self.get_open_action_items()),
            "top_topics": self.transcript_processor.get_top_topics(5),
            "speaker_stats": self.transcript_processor.get_speaker_statistics(),
            "research_context": self.research_context.get_summary(),
        }


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# STREAMLIT UI RENDERER
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

def render_ai_researcher_panel():
    """
    Render the AI Co-Researcher panel in Streamlit.
    Displays transcript processing, action items, meeting notes, and research context.
    """
    import streamlit as st
    import pandas as pd

    st.markdown("""
    <style>
    /* --- GLOBAL SIDEBAR DARK THEMING OVERRIDE --- */
    [data-testid="stSidebar"], section[data-testid="stSidebar"] {
        background-color: #090d16 !important;
        border-right: 1px solid #1e293b !important;
    }
    
    /* Force all sidebar text, links, and headers to high-contrast off-white */
    [data-testid="stSidebar"] *, section[data-testid="stSidebar"] * {
        color: #f8fafc !important;
    }

    /* Target navigation links and text explicitly */
    [data-testid="stSidebarNav"] span, 
    [data-testid="stSidebarNav"] a,
    [data-testid="stSidebarNavLink"],
    [data-testid="stSidebarHeader"] {
        color: #f8fafc !important;
        font-weight: 600 !important;
    }

    /* Navigation item hover state */
    [data-testid="stSidebarNavLink"]:hover,
    [data-testid="stSidebarNav"] a:hover {
        background-color: #1e293b !important;
        border-radius: 8px !important;
    }

    /* Currently selected navigation item active state */
    [data-testid="stSidebarNavLink"][aria-current="page"],
    [data-testid="stSidebarNav"] a[aria-selected="true"] {
        background-color: #0284c7 !important;
        color: #ffffff !important;
        font-weight: 700 !important;
        border-radius: 8px !important;
    }

    /* Custom form inputs inside sidebar */
    section[data-testid="stSidebar"] .stSelectbox label,
    section[data-testid="stSidebar"] .stRadio label,
    section[data-testid="stSidebar"] .stMultiSelect label {
        color: #38bdf8 !important;
        font-weight: 700 !important;
    }
    .ai-researcher-container {
        background: #0f172a;
        border: 1px solid #1e293b;
        border-radius: 16px;
        padding: 1rem;
        margin-bottom: 1rem;
    }
    .ai-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 0.75rem;
        padding-bottom: 0.5rem;
        border-bottom: 1px solid #1e293b;
    }
    .ai-badge {
        display: inline-flex;
        align-items: center;
        gap: 0.3rem;
        padding: 0.15rem 0.5rem;
        border-radius: 999px;
        font-size: 0.65rem;
        font-weight: 700;
    }
    .ai-badge-recording { background: rgba(239,68,68,0.15); color: #f87171; border: 1px solid rgba(239,68,68,0.3); }
    .ai-badge-idle { background: rgba(100,116,139,0.15); color: #94a3b8; border: 1px solid rgba(100,116,139,0.3); }
    .ai-action-item {
        background: #1e293b;
        border-left: 3px solid #6366f1;
        border-radius: 8px;
        padding: 0.75rem;
        margin-bottom: 0.5rem;
    }
    .ai-action-item.critical { border-left-color: #ef4444; }
    .ai-action-item.high { border-left-color: #f59e0b; }
    .ai-action-item.medium { border-left-color: #6366f1; }
    .ai-action-item.low { border-left-color: #64748b; }
    </style>
    """, unsafe_allow_html=True)

    if "ai_researcher" not in st.session_state:
        st.session_state["ai_researcher"] = None

    researcher: Optional[AIResearcher] = st.session_state.get("ai_researcher")

    st.markdown("### ðŸ¤– AI Co-Researcher")

    if not researcher or not researcher.is_recording:
        with st.form("ai_researcher_start"):
            col1, col2 = st.columns([2, 1])
            with col1:
                meeting_title = st.text_input("Meeting Title", value="Research Sync",
                                              key="ai_meeting_title")
            with col2:
                project_id = st.text_input("Project ID", value="proj_001",
                                          key="ai_project_id")

            col3, col4 = st.columns([1, 1])
            with col3:
                user_id = st.text_input("Researcher ID", value="researcher_001",
                                       key="ai_researcher_id")
            with col4:
                st.markdown("<br>", unsafe_allow_html=True)
                if st.form_submit_button("ðŸŽ™ï¸ Start Recording", type="primary",
                                         use_container_width=True):
                    researcher = AIResearcher(project_id, user_id)
                    researcher.start_meeting(meeting_title)
                    st.session_state["ai_researcher"] = researcher
                    st.rerun()
    else:
        # Recording state
        state = researcher.get_meeting_state()
        st.markdown(f"""
        <div class="ai-researcher-container">
            <div class="ai-header">
                <div>
                    <span class="ai-badge ai-badge-recording" style="animation:pulse 2s infinite;">â— Recording</span>
                    <span style="color:#f1f5f9;font-weight:600;margin-left:0.75rem;">{researcher.meeting_title}</span>
                </div>
                <div style="color:#64748b;font-size:0.8rem;">
                    {state['duration_display']} Â· {state['segments_processed']} segments
                </div>
            </div>
        </div>
        <style>
    /* --- GLOBAL SIDEBAR DARK THEMING OVERRIDE --- */
    [data-testid="stSidebar"], section[data-testid="stSidebar"] {
        background-color: #090d16 !important;
        border-right: 1px solid #1e293b !important;
    }
    
    /* Force all sidebar text, links, and headers to high-contrast off-white */
    [data-testid="stSidebar"] *, section[data-testid="stSidebar"] * {
        color: #f8fafc !important;
    }

    /* Target navigation links and text explicitly */
    [data-testid="stSidebarNav"] span, 
    [data-testid="stSidebarNav"] a,
    [data-testid="stSidebarNavLink"],
    [data-testid="stSidebarHeader"] {
        color: #f8fafc !important;
        font-weight: 600 !important;
    }

    /* Navigation item hover state */
    [data-testid="stSidebarNavLink"]:hover,
    [data-testid="stSidebarNav"] a:hover {
        background-color: #1e293b !important;
        border-radius: 8px !important;
    }

    /* Currently selected navigation item active state */
    [data-testid="stSidebarNavLink"][aria-current="page"],
    [data-testid="stSidebarNav"] a[aria-selected="true"] {
        background-color: #0284c7 !important;
        color: #ffffff !important;
        font-weight: 700 !important;
        border-radius: 8px !important;
    }

    /* Custom form inputs inside sidebar */
    section[data-testid="stSidebar"] .stSelectbox label,
    section[data-testid="stSidebar"] .stRadio label,
    section[data-testid="stSidebar"] .stMultiSelect label {
        color: #38bdf8 !important;
        font-weight: 700 !important;
    }
        @keyframes pulse {{ 0%, 100% {{ opacity: 1; }} 50% {{ opacity: 0.5; }} }}
        </style>
        """, unsafe_allow_html=True)

        # Transcript input
        col1, col2 = st.columns([3, 1])
        with col1:
            text = st.text_area("Transcript Input", placeholder="Paste or type meeting transcript here...",
                               height=80, key="ai_transcript_input")
        with col2:
            speaker_name = st.text_input("Speaker", value="You", key="ai_speaker_name")
            source = st.selectbox("Source", options=[s.value for s in TranscriptSource],
                                  index=0, key="ai_transcript_source")

        if st.button("ðŸ“ Process Transcript", type="primary", use_container_width=True) and text:
            researcher.ingest_transcript(
                text=text,
                speaker_id=speaker_name.lower().replace(" ", "_"),
                speaker_name=speaker_name,
                source=TranscriptSource(source),
            )
            st.rerun()

        # Quick action button
        if st.button("ðŸ—£ï¸ Simulate Live Meeting (auto-feed)", use_container_width=True):
            demo_texts = [
                "I think we should analyze the correlation between age and treatment outcome.",
                "Let's run a multiple regression model controlling for baseline variables.",
                "Can you check the p-value for the interaction term?",
                "The results show a significant effect of treatment on recovery time (p < 0.01).",
                "We need to follow up with a power analysis for the next study.",
                "I'll prepare the methodology section for the paper draft.",
                "Should we consider a Bayesian approach instead of frequentist?",
                "The literature review shows mixed evidence for this hypothesis.",
                "Let's schedule a peer review session for next Tuesday.",
                "The data quality check revealed 5% missing values in the outcome variable.",
            ]
            import random
            for t in demo_texts:
                researcher.ingest_transcript(
                    text=t,
                    speaker_id=f"speaker_{random.randint(1,3)}",
                    speaker_name=random.choice(["Dr. Chen", "Prof. Miller", "Dr. Watson"]),
                    source=TranscriptSource.LIVE_SPEECH,
                )
            st.rerun()

        # End meeting
        col1, col2, col3 = st.columns([1, 1, 2])
        with col1:
            if st.button("â¹ï¸ End Meeting", use_container_width=True):
                result = researcher.end_meeting()
                st.success(f"âœ… Meeting ended  {result['duration_display']}")
                st.rerun()
        with col2:
            if st.button("ðŸ§¹ Clear Notes", use_container_width=True):
                researcher.notes.clear()
                researcher.action_items.clear()
                st.rerun()

        # Tabs for different views
        tab1, tab2, tab3, tab4 = st.tabs([
            "ðŸ“‹ Action Items", "ðŸ“ Meeting Notes", " Analytics", "ðŸ”¬ Research Context"
        ])

        with tab1:
            st.markdown(f"### Action Items ({len(researcher.get_open_action_items())} open)")
            open_items = researcher.get_open_action_items()
            if open_items:
                for item in open_items:
                    priority_class = item.priority.value
                    st.markdown(f"""
                    <div class="ai-action-item {priority_class}">
                        <div style="display:flex;justify-content:space-between;">
                            <span style="color:#f1f5f9;font-weight:600;">{item.description[:80]}</span>
                            <span style="color:#64748b;font-size:0.7rem;">{item.confidence:.0%} confidence</span>
                        </div>
                        <div style="color:#64748b;font-size:0.8rem;margin-top:0.25rem;">
                            Priority: {item.priority.value.upper()} Â· Status: {item.status.value}
                            {' Â· ðŸ‘¤ '  item.assignee_name if item.assignee_name else ''}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.info("No action items detected yet. Start speaking or paste transcript.")

        with tab2:
            st.markdown(f"### Meeting Notes ({len(researcher.notes)})")
            categories = list(NoteCategory)
            selected_cat = st.selectbox("Filter by category",
                                         options=["All"]  [c.value for c in categories],
                                         key="ai_note_filter")

            for note in sorted(researcher.notes.values(),
                              key=lambda x: x.generated_at, reverse=True):
                if selected_cat != "All" and note.category.value != selected_cat:
                    continue
                with st.container():
                    st.markdown(f"""
                    <div class="ai-researcher-container" style="padding:0.75rem;">
                        <div style="display:flex;justify-content:space-between;align-items:start;">
                            <div>
                                <span style="color:#818cf8;font-weight:600;font-size:0.85rem;">{note.title}</span>
                                <span class="ai-badge ai-badge-idle" style="margin-left:0.5rem;">{note.category.value}</span>
                            </div>
                            <div style="font-size:0.7rem;color:#64748b;">
                                {datetime.fromtimestamp(note.generated_at).strftime('%H:%M:%S')}
                            </div>
                        </div>
                        <div style="color:#94a3b8;font-size:0.8rem;margin-top:0.3rem;">{note.content[:200]}</div>
                    </div>
                    """, unsafe_allow_html=True)

        with tab3:
            st.markdown("### Meeting Analytics")
            speaker_stats = researcher.transcript_processor.get_speaker_statistics()
            if speaker_stats:
                df = pd.DataFrame([
                    {"Speaker": s["name"],
                     "Segments": s["segments"],
                     "Words": s["total_words"],
                     "Participation %": s["participation_pct"]}
                    for s in speaker_stats.values()
                ])
                st.dataframe(df, use_container_width=True, hide_index=True)

            st.markdown("### Top Topics")
            topics = researcher.transcript_processor.get_top_topics(10)
            if topics:
                df_topics = pd.DataFrame(topics)
                st.dataframe(df_topics, use_container_width=True, hide_index=True)
            else:
                st.info("No topics extracted yet.")

        with tab4:
            st.markdown("### Research Context")
            ctx = researcher.research_context.get_summary()
            ctx_cols = st.columns(3)
            with ctx_cols[0]:
                st.metric("Active Hypotheses", ctx["active_hypotheses"])
            with ctx_cols[1]:
                st.metric("Literature References", ctx["relevant_literature"])
            with ctx_cols[2]:
                st.metric("Findings Logged", ctx["recent_findings"])

            st.markdown("### Integration Hooks")
            for hook_name, active in ctx["integration_hooks"].items():
                st.markdown(f"{'âœ…' if active else 'âŒ'} `{hook_name}`  {'Connected' if active else 'Not connected'}")

            st.info("ðŸ’¡ Connect hooks from Literature Engine, Hypothesis Generator, and AI Analyzer for enriched meeting intelligence.")


