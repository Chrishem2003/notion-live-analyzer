

"""
Text Analyzer  qualitative text analysis with sentiment analysis,
word clouds, theme extraction, and frequency analysis.
"""
from typing import Dict, List, Any, Optional, Tuple
import pandas as pd
import numpy as np
import streamlit as st
import re
from collections import Counter
import warnings

from modules.pandas_compat import text_columns
warnings.filterwarnings('ignore')

# Text processing
try:
    from textblob import TextBlob
    HAS_TEXTBLOB = True
except ImportError:
    HAS_TEXTBLOB = False

try:
    from wordcloud import WordCloud
    HAS_WORDCLOUD = True
except ImportError:
    HAS_WORDCLOUD = False

try:
    import nltk
    from nltk.corpus import stopwords
    nltk.download('stopwords', quiet=True)
    nltk.download('punkt', quiet=True)
    HAS_NLTK = True
except ImportError:
    HAS_NLTK = False


class TextAnalyzer:
    """Qualitative and quantitative text analysis engine."""

    @staticmethod
    def clean_text(text: str) -> str:
        """Clean and normalize text."""
        if not isinstance(text, str):
            return ""
        text = text.lower()
        text = re.sub(r'http\S|www\S|https\S', '', text, flags=re.MULTILINE)
        text = re.sub(r'[^\w\s]', ' ', text)
        text = re.sub(r'\s', ' ', text).strip()
        return text

    @staticmethod
    def get_stopwords(language: str = 'english') -> set:
        """Get stopwords for specified language."""
        if HAS_NLTK:
            try:
                return set(stopwords.words(language))
            except Exception:
                pass
        # Default English stopwords
        return {
            'a', 'an', 'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'by', 'with', 'from', 'is', 'are', 'was', 'were', 'be', 'been',
            'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would',
            'can', 'could', 'shall', 'should', 'may', 'might', 'must', 'about',
            'into', 'through', 'during', 'before', 'after', 'above', 'below',
            'between', 'out', 'off', 'over', 'under', 'again', 'further', 'then',
            'once', 'here', 'there', 'when', 'where', 'why', 'how', 'all', 'each',
            'every', 'both', 'few', 'more', 'most', 'other', 'some', 'such', 'no',
            'not', 'only', 'own', 'same', 'so', 'than', 'too', 'very', 'just',
            'because', 'as', 'until', 'while', 'it', 'its', 'this', 'that', 'these',
            'those', 'i', 'me', 'my', 'myself', 'we', 'our', 'ours', 'ourselves',
            'you', 'your', 'yours', 'yourself', 'yourselves', 'he', 'him', 'his',
            'himself', 'she', 'her', 'hers', 'herself', 'they', 'them', 'their',
            'theirs', 'themselves', 'what', 'which', 'who', 'whom',
        }

    @staticmethod
    def get_word_frequencies(
        texts: List[str],
        top_n: int = 50,
        min_length: int = 3,
        remove_stopwords: bool = True,
        language: str = 'english',
    ) -> pd.DataFrame:
        """Get word frequency counts from a list of texts."""
        stop_words = TextAnalyzer.get_stopwords(language) if remove_stopwords else set()
        all_words = []

        for text in texts:
            cleaned = TextAnalyzer.clean_text(str(text))
            words = cleaned.split()
            for word in words:
                if len(word) >= min_length and (not remove_stopwords or word not in stop_words):
                    all_words.append(word)

        counter = Counter(all_words)
        most_common = counter.most_common(top_n)

        df = pd.DataFrame(most_common, columns=['Word', 'Frequency'])
        df['Percentage'] = round(df['Frequency'] / df['Frequency'].sum() * 100, 2)
        df['Rank'] = range(1, len(df)  1)
        return df

    @staticmethod
    def generate_wordcloud(
        texts: List[str],
        width: int = 800,
        height: int = 400,
        background_color: str = 'white',
        max_words: int = 200,
    ) -> Optional[Any]:
        """Generate a word cloud image."""
        if not HAS_WORDCLOUD:
            return None

        full_text = ' '.join(str(t) for t in texts if isinstance(t, str))
        if not full_text.strip():
            return None

        wc = WordCloud(
            width=width, height=height,
            background_color=background_color,
            max_words=max_words,
            stopwords=TextAnalyzer.get_stopwords(),
            collocations=False,
            colormap='viridis',
            random_state=42,
        ).generate(full_text)

        return wc

    @staticmethod
    def analyze_sentiment(texts: List[str]) -> pd.DataFrame:
        """Analyze sentiment of texts using TextBlob."""
        if not HAS_TEXTBLOB:
            # Fallback: simple keyword-based
            positive_words = {'good', 'great', 'excellent', 'amazing', 'wonderful', 'fantastic',
                              'happy', 'love', 'beautiful', 'best', 'positive', 'success',
                              'beneficial', 'impressive', 'outstanding', 'perfect'}
            negative_words = {'bad', 'terrible', 'awful', 'horrible', 'poor', 'worst',
                              'hate', 'ugly', 'negative', 'failure', 'problem', 'issue',
                              'difficult', 'worse', 'painful', 'disappointing'}

            results = []
            for text in texts:
                cleaned = TextAnalyzer.clean_text(str(text))
                words = set(cleaned.split())
                pos_count = len(words & positive_words)
                neg_count = len(words & negative_words)
                polarity = (pos_count - neg_count) / max(len(words), 1)
                subjectivity = (pos_count  neg_count) / max(len(words), 1)

                if polarity > 0.1:
                    sentiment = 'Positive'
                elif polarity < -0.1:
                    sentiment = 'Negative'
                else:
                    sentiment = 'Neutral'

                results.append({
                    'Text': str(text)[:200],
                    'Sentiment': sentiment,
                    'Polarity': round(polarity, 4),
                    'Subjectivity': round(subjectivity, 4),
                })
            return pd.DataFrame(results)

        results = []
        for text in texts:
            if not isinstance(text, str) or not text.strip():
                continue
            try:
                blob = TextBlob(text)
                polarity = blob.sentiment.polarity
                subjectivity = blob.sentiment.subjectivity

                if polarity > 0.1:
                    sentiment = 'Positive'
                elif polarity < -0.1:
                    sentiment = 'Negative'
                else:
                    sentiment = 'Neutral'

                results.append({
                    'Text': str(text)[:200],
                    'Sentiment': sentiment,
                    'Polarity': round(polarity, 4),
                    'Subjectivity': round(subjectivity, 4),
                })
            except Exception:
                continue

        return pd.DataFrame(results)

    @staticmethod
    def extract_ngrams(
        texts: List[str],
        n: int = 2,
        top_n: int = 20,
        min_freq: int = 2,
    ) -> pd.DataFrame:
        """Extract n-grams (bigrams, trigrams, etc.) from texts."""
        all_tokens = []
        for text in texts:
            cleaned = TextAnalyzer.clean_text(str(text))
            tokens = cleaned.split()
            all_tokens.extend(tokens)

        if len(all_tokens) < n:
            return pd.DataFrame()

        ngrams = zip(*[all_tokens[i:] for i in range(n)])
        ngram_list = [' '.join(ng) for ng in ngrams]

        counter = Counter(ngram_list)
        common = [(ng, freq) for ng, freq in counter.most_common(top_n) if freq >= min_freq]

        return pd.DataFrame(common, columns=['N-Gram', 'Frequency'])

    @staticmethod
    def extract_keywords(
        texts: List[str],
        method: str = 'frequency',
        top_n: int = 20,
    ) -> pd.DataFrame:
        """Extract keywords from texts."""
        if method == 'frequency':
            return TextAnalyzer.get_word_frequencies(texts, top_n=top_n)

        # TF-IDF like scoring
        stop_words = TextAnalyzer.get_stopwords()
        doc_count = len(texts)
        word_doc_freq = Counter()
        word_total_freq = Counter()

        for text in texts:
            cleaned = TextAnalyzer.clean_text(str(text))
            words = set(cleaned.split())
            for word in words:
                if len(word) >= 3 and word not in stop_words:
                    word_doc_freq[word] = 1
            for word in cleaned.split():
                if len(word) >= 3 and word not in stop_words:
                    word_total_freq[word] = 1

        tfidf_scores = {}
        for word, total_freq in word_total_freq.most_common(top_n * 3):
            tf = total_freq
            idf = np.log((doc_count  1) / (word_doc_freq.get(word, 0)  1))  1
            tfidf_scores[word] = tf * idf

        top_keywords = sorted(tfidf_scores.items(), key=lambda x: x[1], reverse=True)[:top_n]
        return pd.DataFrame(top_keywords, columns=['Keyword', 'TF-IDF Score'])

    @staticmethod
    def text_summary(texts: List[str]) -> Dict[str, Any]:
        """Generate a summary of text corpus statistics."""
        all_text = ' '.join(str(t) for t in texts if isinstance(t, str))
        if not all_text.strip():
            return {"error": "No valid text found"}

        cleaned = TextAnalyzer.clean_text(all_text)
        words = cleaned.split()
        sentences = all_text.split('.')

        # Vocabulary richness (type-token ratio)
        unique_words = len(set(words))
        total_words = len(words)
        ttr = unique_words / max(total_words, 1)

        # Average word length
        avg_word_len = sum(len(w) for w in words) / max(len(words), 1)

        return {
            "total_texts": len(texts),
            "total_words": total_words,
            "total_unique_words": unique_words,
            "type_token_ratio": round(ttr, 4),
            "avg_word_length": round(avg_word_len, 2),
            "avg_words_per_text": round(total_words / max(len(texts), 1), 1),
            "estimated_sentences": len([s for s in sentences if s.strip()]),
        }


# ─── UI ─────────────────────────────────────────────────────────────

def render_text_analysis_ui(df: pd.DataFrame):
    """Render the text analysis UI."""
    st.markdown("## 💬 Text & Qualitative Analysis")
    st.markdown("*Sentiment analysis, word clouds, frequency analysis, keyword extraction*")

    if df is None or df.empty:
        st.warning("No data available. Load data first.")
        return

    # Select text column
    text_cols = text_columns(df)
    if not text_cols:
        st.warning("No text columns found in the dataset.")
        return

    text_col = st.selectbox("Select text column to analyze", options=text_cols, key="text_col")
    texts = df[text_col].dropna().tolist()

    if df[text_col].nunique() < 3:
        st.warning("Selected column has too few unique text values. Select a different column.")
        return

    st.info(f"**Analyzing**: {len(texts)} text entries from '{text_col}'")

    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        " Summary", "😊 Sentiment", "📈 Word Frequency",
        "☁️ Word Cloud", "🔤 N-Grams"
    ])

    with tab1:
        st.subheader(" Corpus Summary")
        if st.button("Generate Summary", type="primary"):
            summary = TextAnalyzer.text_summary(texts)
            if "error" not in summary:
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Total Texts", summary.get("total_texts", 0))
                with col2:
                    st.metric("Total Words", f"{summary.get('total_words', 0):,}")
                with col3:
                    st.metric("Unique Words", f"{summary.get('total_unique_words', 0):,}")
                with col4:
                    st.metric("Type-Token Ratio", f"{summary.get('type_token_ratio', 0):.3f}")
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Avg Word Length", summary.get("avg_word_length", 0))
                with col2:
                    st.metric("Avg Words/Text", summary.get("avg_words_per_text", 0))
            else:
                st.error(summary["error"])

    with tab2:
        st.subheader("😊 Sentiment Analysis")
        st.caption("Analyze the sentiment polarity of text entries")

        if st.button("Run Sentiment Analysis", type="primary"):
            with st.spinner("Analyzing sentiment..."):
                sentiment_df = TextAnalyzer.analyze_sentiment(texts)

            if not sentiment_df.empty:
                # Sentiment distribution
                dist = sentiment_df['Sentiment'].value_counts()
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Positive", int(dist.get('Positive', 0)))
                with col2:
                    st.metric("Neutral", int(dist.get('Neutral', 0)))
                with col3:
                    st.metric("Negative", int(dist.get('Negative', 0)))

                # Average polarity
                avg_pol = sentiment_df['Polarity'].mean()
                avg_subj = sentiment_df['Subjectivity'].mean()
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Avg Polarity", f"{avg_pol:.3f}",
                              delta="Positive" if avg_pol > 0 else "Negative" if avg_pol < 0 else "Neutral")
                with col2:
                    st.metric("Avg Subjectivity", f"{avg_subj:.3f}",
                              delta="Subjective" if avg_subj > 0.5 else "Objective")

                # Polarity distribution chart
                import plotly.express as px
                fig = px.histogram(sentiment_df, x='Polarity', color='Sentiment',
                                   nbins=30, title='Sentiment Polarity Distribution',
                                   color_discrete_map={
                                       'Positive': '#2ecc71', 'Neutral': '#95a5a6', 'Negative': '#e74c3c'
                                   })
                st.plotly_chart(fig, use_container_width=True)

                # Show data
                st.dataframe(sentiment_df.head(50), use_container_width=True, hide_index=True)
            else:
                st.warning("No sentiment results. TextBlob may not be installed.")

    with tab3:
        st.subheader("📈 Word Frequency Analysis")
        st.caption("Find the most frequent words in the text corpus")

        col1, col2 = st.columns(2)
        with col1:
            top_n = st.slider("Number of words", 10, 100, 30, key="wf_top")
        with col2:
            min_len = st.slider("Min word length", 2, 10, 3, key="wf_minlen")

        if st.button("Get Word Frequencies", type="primary"):
            freq_df = TextAnalyzer.get_word_frequencies(texts, top_n=top_n, min_length=min_len)

            if not freq_df.empty:
                st.dataframe(freq_df, use_container_width=True, hide_index=True)

                # Bar chart
                import plotly.express as px
                fig = px.bar(freq_df.head(20), x='Word', y='Frequency',
                             title=f'Top {min(20, len(freq_df))} Words by Frequency',
                             color='Frequency', color_continuous_scale='Viridis')
                fig.update_layout(xaxis_tickangle=-45)
                st.plotly_chart(fig, use_container_width=True)

                # Export
                csv = freq_df.to_csv(index=False).encode('utf-8')
                import base64
                b64 = base64.b64encode(csv).decode()
                st.markdown(f'<a href="data:text/csv;base64,{b64}" download="word_frequencies.csv">📥 Download CSV</a>',
                           unsafe_allow_html=True)

    with tab4:
        st.subheader("☁️ Word Cloud")
        st.caption("Visualize word frequency as a word cloud")

        if HAS_WORDCLOUD:
            col1, col2 = st.columns(2)
            with col1:
                wc_max = st.slider("Max words", 50, 500, 200, key="wc_max")
            with col2:
                wc_bg = st.selectbox("Background", ['white', 'black', 'gray', '#1a1a2e'], key="wc_bg")

            if st.button("Generate Word Cloud", type="primary"):
                with st.spinner("Generating word cloud..."):
                    wc = TextAnalyzer.generate_wordcloud(texts, max_words=wc_max, background_color=wc_bg)

                if wc:
                    import matplotlib.pyplot as plt
                    fig, ax = plt.subplots(figsize=(10, 5))
                    ax.imshow(wc, interpolation='bilinear')
                    ax.axis('off')
                    st.pyplot(fig)
                    plt.close()

                    # Save option
                    import io
                    import base64
                    buf = io.BytesIO()
                    wc.to_image().save(buf, format='PNG')
                    b64 = base64.b64encode(buf.getvalue()).decode()
                    st.markdown(f'<a href="data:image/png;base64,{b64}" download="wordcloud.png">📥 Download PNG</a>',
                               unsafe_allow_html=True)
                else:
                    st.warning("Could not generate word cloud. Not enough text data.")
        else:
            st.warning("WordCloud library not installed. Install with: pip install wordcloud")

    with tab5:
        st.subheader("🔤 N-Gram Analysis")
        st.caption("Find common word combinations (bigrams, trigrams, etc.)")

        col1, col2 = st.columns(2)
        with col1:
            n_gram_size = st.selectbox("N-gram size", options=[2, 3, 4, 5], index=0, key="ng_size",
                                       format_func=lambda x: f"{x}-grams ({['Bi', 'Tri', '4', '5'][x-2]}grams)")
        with col2:
            ng_top = st.slider("Top N", 10, 50, 20, key="ng_top")

        if st.button("Extract N-Grams", type="primary"):
            ng_df = TextAnalyzer.extract_ngrams(texts, n=n_gram_size, top_n=ng_top)

            if not ng_df.empty:
                st.dataframe(ng_df, use_container_width=True, hide_index=True)

                import plotly.express as px
                fig = px.bar(ng_df.head(15), x='N-Gram', y='Frequency',
                             title=f'Top {min(15, len(ng_df))} {n_gram_size}-grams',
                             color='Frequency', color_continuous_scale='Viridis')
                fig.update_layout(xaxis_tickangle=-45)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Not enough data for n-gram extraction. Try a smaller n-gram size.")

