import feedparser # Add import
import re # For keyword searching
import feedparser
import re
from ..models.agent_models import AgentConfigOutput, AgentStrategyConfig
from ..models.event_bus_models import Event, NewsArticleEventPayload
from ..services.event_bus_service import EventBusService
from .learning_data_logger_service import LearningDataLoggerService # Added
from ..models.learning_models import LearningLogEntry # Added
from typing import List, Dict, Any, Optional, Set, Literal # Added Literal for _perform_basic_sentiment
from loguru import logger
from datetime import datetime, timezone, timedelta
from dateutil import parser as date_parser
import asyncio

class NewsAnalysisService:
    def __init__(
        self,
        agent_config: AgentConfigOutput,
        event_bus: EventBusService,
        learning_logger_service: Optional[LearningDataLoggerService] = None # Added
    ):
        self.agent_config = agent_config
        self.event_bus = event_bus
        self.learning_logger_service = learning_logger_service # Store it

        if self.agent_config.strategy.news_analysis_params:
            self.params = self.agent_config.strategy.news_analysis_params
        else:
            logger.warning(f"NewsSvc ({self.agent_config.agent_id}): news_analysis_params not found. Using defaults.")
            self.params = AgentStrategyConfig.NewsAnalysisParams()

        if self.learning_logger_service:
            logger.info(f"NewsSvc ({self.agent_config.agent_id}): LearningDataLoggerService: Available")
        else:
            logger.warning(f"NewsSvc ({self.agent_config.agent_id}): LearningDataLoggerService: Not Available. Learning logs will be skipped.")

    async def _log_learning_event(
        self,
        event_type: str,
        data_snapshot: Dict,
        outcome: Optional[Dict] = None,
        notes: Optional[str] = None,
        tags: Optional[List[str]] = None
    ):
        if self.learning_logger_service:
            entry = LearningLogEntry(
                primary_agent_id=self.agent_config.agent_id,
                source_service=self.__class__.__name__,
                event_type=event_type,
                data_snapshot=data_snapshot,
                outcome_or_result=outcome,
                notes=notes,
                tags=tags if tags else []
            )
            await self.learning_logger_service.log_entry(entry)

    def _perform_basic_sentiment(self, text: str) -> Dict[str, Any]:
        text_lower = text.lower()
        score = 0
        matched_keywords_found: List[str] = []

        for kw in self.params.keywords_positive:
            if kw.lower() in text_lower: # Simple substring check
                score += 1
                matched_keywords_found.append(kw)
        for kw in self.params.keywords_negative:
            if kw.lower() in text_lower: # Simple substring check
                score -= 1
                matched_keywords_found.append(kw)

        # Normalize score (e.g. if many keywords match, cap it or use a more nuanced scoring)
        # For this basic version, raw score is fine. Can be scaled to -1 to 1 if needed.
        # Example scaling: max_possible_score = len(self.params.keywords_positive) + len(self.params.keywords_negative)
        # if max_possible_score > 0: normalized_score = score / max_possible_score else 0
        # For now, use raw score for simplicity.

        label: Literal["positive", "negative", "neutral"] = "neutral"
        if score > 0: label = "positive"
        elif score < 0: label = "negative"

        return {"score": float(score), "label": label, "matched": list(set(matched_keywords_found))}


    async def fetch_and_analyze_feeds(self):
        logger.info(f"NewsAnalysisService ({self.agent_config.agent_id}): Starting feed fetch and analysis. Feeds: {self.params.rss_feed_urls}")
        if not self.params.rss_feed_urls:
            logger.warning(f"NewsAnalysisService ({self.agent_config.agent_id}): No RSS feed URLs configured.")
            return

        processed_links: Set[str] = set()

        for feed_url in self.params.rss_feed_urls:
            logger.debug(f"NewsAnalysisService ({self.agent_config.agent_id}): Fetching feed: {feed_url}")
            try:
                # feedparser.parse is synchronous. For a truly async service, run in executor.
                # Using run_in_executor for better async behavior.
                loop = asyncio.get_event_loop()
                feed = await loop.run_in_executor(None, feedparser.parse, feed_url)

            except Exception as e:
                logger.error(f"NewsAnalysisService ({self.agent_config.agent_id}): Error fetching or parsing feed {feed_url}: {e}", exc_info=True)
                continue # Skip to next feed URL

            entries_to_process = feed.entries
            if self.params.fetch_limit_per_feed is not None and self.params.fetch_limit_per_feed > 0:
                entries_to_process = feed.entries[:self.params.fetch_limit_per_feed]

            logger.debug(f"Processing {len(entries_to_process)} entries from {feed_url} (limit: {self.params.fetch_limit_per_feed})")

            for entry in entries_to_process:
                link = entry.get("link")
                if not link or link in processed_links:
                    logger.trace(f"Skipping entry (no link or already processed): {link or 'No link'}")
                    continue
                processed_links.add(link)

                headline = entry.get("title", "No Title")
                # Combine summary and content if available for better analysis text
                summary_text = entry.get("summary", "")
                content_text = ""
                if hasattr(entry, 'content') and entry.content:
                    # entry.content can be a list of content objects
                    if isinstance(entry.content, list) and entry.content:
                        content_text = entry.content[0].get('value', "") if entry.content[0] else ""
                    elif isinstance(entry.content, dict): # Less common but possible
                        content_text = entry.content.get('value', "")

                full_text_for_analysis = f"{headline} {summary_text} {content_text}".strip()

                published_dt: Optional[datetime] = None
                published_parsed = entry.get("published_parsed") or entry.get("updated_parsed")
                if published_parsed:
                    try:
                        published_dt = datetime(*published_parsed[:6], tzinfo=timezone.utc)
                    except Exception as e_date:
                        logger.warning(f"Could not parse 'published_parsed' struct for '{link}': {e_date}")
                elif entry.get("published"):
                    try:
                        published_dt = date_parser.parse(entry.get("published")).astimezone(timezone.utc)
                    except Exception as e_date_str:
                        logger.warning(f"Could not parse 'published' string for '{link}': {e_date_str}")

                text_to_analyze_lower = full_text_for_analysis.lower()

                mentioned_symbols_found: List[str] = []
                if self.params.symbols_of_interest:
                    for sym in self.params.symbols_of_interest:
                        # Using word boundaries for symbol matching to avoid partial matches (e.g., "MANA" in "HuMANity")
                        # Regex needs to be careful with special characters in symbols (e.g., '/')
                        try:
                            # Simple check if symbol (as a word) is in text.
                            # More robust: check for common prefixes like $ or specific formats.
                            if re.search(r'\b' + re.escape(sym.lower()) + r'\b', text_to_analyze_lower):
                                mentioned_symbols_found.append(sym)
                        except re.error as re_err:
                            logger.warning(f"Regex error for symbol '{sym}': {re_err}")

                sentiment_analysis = self._perform_basic_sentiment(text_to_analyze_lower) # Pass lowercased text

                payload = NewsArticleEventPayload(
                    source_feed_url=feed_url,
                    headline=headline,
                    link=link,
                    published_date=published_dt,
                    summary=summary_text[:500] if summary_text else None,
                    mentioned_symbols=list(set(mentioned_symbols_found)), # Ensure unique symbols
                    sentiment_score=sentiment_analysis["score"],
                    sentiment_label=sentiment_analysis["label"],
                    matched_keywords=sentiment_analysis["matched"],
                    raw_content_snippet=full_text_for_analysis[:200] if full_text_for_analysis else None
                )

                await self._log_learning_event(
                    event_type="NewsArticleProcessed",
                    data_snapshot=payload.model_dump(exclude_none=True),
                    notes=f"News article processed: {payload.headline[:100]}...",
                    tags=["news_analysis", payload.sentiment_label] + [f"symbol:{s}" for s in payload.mentioned_symbols]
                )

                event = Event(
                    publisher_agent_id=self.agent_config.agent_id,
                    message_type="NewsArticleEvent",
                    payload=payload.model_dump(exclude_none=True)
                )
                await self.event_bus.publish(event)
                logger.debug(f"NewsSvc ({self.agent_config.agent_id}): Published NewsArticleEvent for: {headline[:50]}...")
        logger.info(f"NewsSvc ({self.agent_config.agent_id}): Finished feed fetch and analysis cycle.")
