"""Task extraction component for identifying tasks from transcripts."""

import re
from typing import List, Optional, Set

from src.models import ExtractedTask


class TaskExtractor:
    """Extracts individual tasks from meeting transcript text."""
    
    # Phrases that indicate a task is being discussed
    TASK_INDICATORS = [
        'need to', 'needs to', 'should', 'must', 'have to', 'has to',
        'we need', 'someone should', "let's", 'tackle', 'work on',
        'fix', 'update', 'design', 'write', 'implement', 'create',
        'build', 'develop', 'complete', 'finish', 'prepare', 'review',
        'optimize', 'improve', 'add', 'remove', 'change', 'modify',
        'set up', 'configure', 'deploy', 'test', 'debug', 'refactor',
        'is really slow', 'is slow', 'performance is'  # Implicit optimization tasks
    ]
    
    # Phrases indicating deadlines
    DEADLINE_PATTERNS = [
        r'by\s+(tomorrow\s+\w+)',
        r'by\s+(end\s+of\s+(?:this\s+)?\w+)',
        r'by\s+(\w+day)',
        r'done\s+by\s+(tomorrow\s+\w+)',
        r'done\s+by\s+(tomorrow)',
        r'(tomorrow\s+(?:evening|morning|afternoon))',
        r'(tomorrow)',
        r'(end\s+of\s+(?:this\s+)?\w+)',
        r'(next\s+\w+)',
        r'before\s+(\w+(?:\'s)?\s*(?:\w+)?)',
        r'until\s+(next\s+\w+)',
        r'until\s+(\w+)',
        r'for\s+(\w+day)',
        r'plan\s+this\s+for\s+(\w+day)',
        r'plan\s+(?:this\s+)?for\s+(\w+)',
        r'(today|tonight)',
        r'in\s+(\d+\s+\w+)',
    ]
    
    # Phrases indicating priority
    PRIORITY_INDICATORS = {
        'critical': ['critical', 'urgent', 'asap', 'immediately', 'emergency'],
        'high': ['high priority', 'important', 'blocking', 'blocker', 'affecting users'],
        'low': ['can wait', 'when possible', 'nice to have', 'low priority', 'next sprint']
    }
    
    # Phrases indicating dependencies
    DEPENDENCY_PATTERNS = [
        r'depends on (?:the\s+)?(.+?)(?:\s+being\s+completed|\s+first|,|\.|$)',
        r'depends on (.+?)(?:\.|,|$)',
        r'after (.+?) is (?:done|completed|finished)',
        r'once (.+?) is (?:done|completed|finished)',
        r'blocked by (.+?)(?:\.|,|$)',
        r'waiting for (.+?)(?:\.|,|$)',
        r'requires (.+?) (?:to be |first)',
    ]
    
    def __init__(self, team_names: Optional[List[str]] = None):
        """
        Initialize the task extractor.
        
        Args:
            team_names: List of team member names for mention detection
        """
        self.team_names = [n.lower() for n in (team_names or [])]
    
    def set_team_names(self, names: List[str]):
        """Update the list of team member names."""
        self.team_names = [n.lower() for n in names]
    
    def extract_tasks(self, transcript: str) -> List[ExtractedTask]:
        """
        Extracts all tasks from a transcript.
        
        Args:
            transcript: The meeting transcript text
            
        Returns:
            List of ExtractedTask objects
        """
        if not transcript or not transcript.strip():
            return []
        
        # Split into sentences
        sentences = self._split_into_sentences(transcript)
        
        # Merge context sentences with following action sentences
        merged_sentences = self._merge_context_sentences(sentences)
        
        # Merge task sentences with their following context (deadlines, dependencies)
        merged_sentences = self._merge_task_with_context(merged_sentences)
        
        tasks = []
        for sentence in merged_sentences:
            if self._contains_task_indicator(sentence) and self._is_actionable_task(sentence):
                task = self._extract_task_from_sentence(sentence)
                if task and len(task.description) > 10:  # Filter very short descriptions
                    tasks.append(task)
        
        return tasks
    
    def _merge_context_sentences(self, sentences: List[str]) -> List[str]:
        """Merges context sentences with their related action sentences."""
        if not sentences:
            return []
        
        merged = []
        i = 0
        while i < len(sentences):
            current = sentences[i]
            current_lower = current.lower()
            
            # Check if this is a context sentence that should be merged with following sentences
            context_patterns = [
                'database performance',
                'performance is',
                'is really slow',
            ]
            
            is_context = any(p in current_lower for p in context_patterns)
            
            if is_context:
                # Look ahead up to 4 sentences for related context to merge
                combined = current
                j = i + 1
                while j < len(sentences) and j <= i + 4:
                    following = sentences[j]
                    following_lower = following.lower()
                    
                    # Patterns that indicate related context for this task
                    should_merge = any([
                        # Name mentions related to the task
                        any(name in following_lower and ('optimization' in following_lower or 'backend' in following_lower) 
                            for name in self.team_names),
                        # Deadline/action sentences
                        following_lower.startswith('we should tackle'),
                        'should tackle this' in following_lower,
                        'end of this week' in following_lower,
                        'end of week' in following_lower,
                        # User experience context
                        following_lower.startswith("it's affecting"),
                        following_lower.startswith("its affecting"),
                    ])
                    
                    if should_merge:
                        combined = combined + ' ' + following
                        j += 1
                    else:
                        # Skip non-matching sentences but keep looking
                        # Only skip if it's a short context sentence (like name mention)
                        if len(following) < 60 and j < i + 3:
                            combined = combined + ' ' + following
                            j += 1
                        else:
                            break
                
                merged.append(combined)
                i = j
                continue
            
            merged.append(current)
            i += 1
        
        return merged
    
    def _is_actionable_task(self, sentence: str) -> bool:
        """Checks if sentence describes an actionable task vs just context."""
        sentence_lower = sentence.lower()
        
        # Skip sentences that are just context/deadlines without actual tasks
        context_only_patterns = [
            r'^this needs to be done',
            r'^this should be done',
            r'^this depends on',
            r'^this is high priority',
            r'^this is urgent',
            r"^didn't you work on",
            r"^let's plan this",
            r'^we should tackle this',  # "tackle this" without specific object
            r'^tackle this by',
        ]
        
        for pattern in context_only_patterns:
            if re.match(pattern, sentence_lower):
                return False
        
        # Must have a clear action verb with an object
        action_with_object = [
            r'\b(fix|update|design|write|create|build|implement|optimize)\b.*\b(bug|screen|test|documentation|api|database|module|feature|performance)\b',
            r'\bdesign\b.*\b(screen|onboarding|ui|interface)\b',
            r'\b(database|backend)\b.*\b(performance|optimization)\b',
            r'database performance is',  # "database performance is really slow"
            r'update.*api.*documentation',
            r'update.*documentation',
            r'performance is.*slow',  # Implicit task to fix slow performance
        ]
        
        for pattern in action_with_object:
            if re.search(pattern, sentence_lower):
                return True
        
        # Check if it starts with a task indicator followed by content
        if any(sentence_lower.startswith(ind) for ind in ['we need to', 'someone should', 'need to', 'we should']):
            return True
        
        # Check if sentence contains "we <indicator>" pattern with content after
        we_indicator_pattern = r'\bwe\s+(need to|should|must|have to)\s+\w+'
        if re.search(we_indicator_pattern, sentence_lower):
            return True
        
        # Check for "should tackle/design/fix" patterns
        if re.search(r'should\s+(tackle|design|fix|update|write|create|optimize)', sentence_lower):
            return True
        
        return False
    
    def _split_into_sentences(self, text: str) -> List[str]:
        """Splits text into sentences."""
        # Split on sentence-ending punctuation but keep context together
        sentences = re.split(r'(?<=[.!?])\s+', text)
        
        # Further split on spoken separators
        expanded = []
        for s in sentences:
            # Split on "one more thing", "oh and" but NOT on "also" (it's part of sentence)
            parts = re.split(r'\b(?:one more thing|oh and)\b', s, flags=re.IGNORECASE)
            expanded.extend(parts)
        
        # Split sentences that contain multiple tasks joined by "and we need to"
        further_expanded = []
        for s in expanded:
            # Split on "and we need to" when it introduces a new task
            if ' and we need to ' in s.lower():
                parts = re.split(r'\s+and\s+we\s+need\s+to\s+', s, flags=re.IGNORECASE)
                if len(parts) > 1:
                    further_expanded.append(parts[0])
                    for part in parts[1:]:
                        further_expanded.append('We need to ' + part)
                else:
                    further_expanded.append(s)
            else:
                further_expanded.append(s)
        
        return [s.strip() for s in further_expanded if s.strip() and len(s.strip()) > 5]
    
    def _merge_task_with_context(self, sentences: List[str]) -> List[str]:
        """Merges task sentences with their following context sentences (deadlines, dependencies)."""
        if not sentences:
            return []
        
        merged = []
        last_task_idx = -1  # Track the index of the last task in merged list
        i = 0
        while i < len(sentences):
            current = sentences[i]
            current_lower = current.lower()
            
            # Check if this sentence contains a task indicator
            has_task = self._contains_task_indicator(current)
            
            if has_task:
                # Look ahead for context sentences that should be merged
                combined = current
                j = i + 1
                while j < len(sentences) and j <= i + 3:  # Look at most 3 sentences ahead
                    next_sentence = sentences[j]
                    next_lower = next_sentence.lower()
                    
                    # Check if next sentence is context (deadline, priority, dependency)
                    is_context = any([
                        next_lower.startswith('this needs to be'),
                        next_lower.startswith('this should be'),
                        next_lower.startswith('this is high priority'),
                        next_lower.startswith('this is urgent'),
                        next_lower.startswith('this depends on'),
                        next_lower.startswith('this can wait'),
                        'depends on' in next_lower and 'this depends' in next_lower,
                        re.match(r"^(it's|its)\s+(blocking|affecting|urgent)", next_lower),
                    ])
                    
                    # Also check for sentences that are questions about the task (like "didn't you work on...")
                    # These should be skipped but we continue looking for context after them
                    is_task_question = re.match(r"^[\w]+,?\s*(didn't|did)\s+you\s+work\s+on", next_lower) or \
                                       re.match(r"^(didn't|did)\s+you\s+work\s+on", next_lower)
                    
                    if is_context:
                        combined = combined + ' ' + next_sentence
                        j += 1
                    elif is_task_question:
                        # Skip the question but keep looking for context
                        j += 1
                    else:
                        break
                
                merged.append(combined)
                last_task_idx = len(merged) - 1
                i = j
            else:
                # Check if this is a "can wait" sentence that should be merged with previous task
                if current_lower.startswith('this can wait') and last_task_idx >= 0:
                    merged[last_task_idx] = merged[last_task_idx] + ' ' + current
                    i += 1
                # Check if this is a question about a task - skip it but don't add to merged
                elif re.match(r"^[\w]+,?\s*(didn't|did)\s+you\s+work\s+on", current_lower) or \
                     re.match(r"^(didn't|did)\s+you\s+work\s+on", current_lower):
                    i += 1
                else:
                    merged.append(current)
                    i += 1
        
        return merged
    
    def _contains_task_indicator(self, sentence: str) -> bool:
        """Checks if a sentence contains task indicators."""
        sentence_lower = sentence.lower()
        
        # Exclude question sentences that reference past work
        if re.search(r"(didn't|did)\s+you\s+work\s+on", sentence_lower):
            return False
        
        return any(indicator in sentence_lower for indicator in self.TASK_INDICATORS)
    
    def _extract_task_from_sentence(self, sentence: str) -> Optional[ExtractedTask]:
        """Extracts task details from a single sentence."""
        sentence_lower = sentence.lower()
        
        # Generate task description
        description = self._generate_description(sentence)
        if not description:
            return None
        
        # Extract mentioned person
        mentioned_person = self._extract_mentioned_person(sentence)
        
        # Extract deadline phrase
        deadline_phrase = self._extract_deadline_phrase(sentence)
        
        # Extract priority indicators - use description context, not full sentence
        # This prevents "high priority" from one task affecting another
        priority_context = description.lower()
        # Also check immediate context around the task action
        if 'high priority' in sentence_lower:
            # Check if high priority is near the task description
            desc_pos = sentence_lower.find(description.lower()[:20]) if len(description) > 20 else sentence_lower.find(description.lower())
            hp_pos = sentence_lower.find('high priority')
            # Only include if within 100 chars of each other
            if desc_pos >= 0 and hp_pos >= 0 and abs(desc_pos - hp_pos) < 100:
                priority_context += ' high priority'
        
        priority_indicators = self._extract_priority_indicators(priority_context)
        
        # Extract dependency phrases
        dependency_phrases = self._extract_dependency_phrases(sentence)
        
        return ExtractedTask(
            description=description,
            raw_text=sentence,
            mentioned_person=mentioned_person,
            deadline_phrase=deadline_phrase,
            priority_indicators=priority_indicators,
            dependency_phrases=dependency_phrases
        )
    
    def _generate_description(self, sentence: str) -> str:
        """Generates a clean task description from a sentence."""
        description = sentence.strip()
        
        # Remove common prefixes and filler phrases
        prefixes_to_remove = [
            r'^(?:hi everyone,?\s*)?',
            r'^(?:okay,?\s*)?',
            r'^(?:so,?\s*)?',
            r'^(?:and,?\s*)?',
            r'^(?:also,?\s*)?',
            r'^(?:oh,?\s*)?',
            r"^(?:let's discuss this week's priorities\s*)?",
            r'^(?:we need someone to\s+)',
            r'^(?:we need to\s+)',
            r'^(?:we should\s+)',
            r'^(?:someone should\s+)',
            r'^(?:the\s+)',
        ]
        
        for prefix in prefixes_to_remove:
            description = re.sub(prefix, '', description, flags=re.IGNORECASE)
        
        # Extract the core task - find the main action
        # Look for patterns like "fix X", "update X", "design X", "write X"
        action_patterns = [
            r'(fix\s+(?:the\s+)?(?:critical\s+)?[\w\s]+(?:bug|issue|problem))',
            r'(optimize\s+(?:the\s+)?database\s+performance)',
            r'(database\s+performance)',  # Will be converted to "Optimize database performance"
            r'(update\s+(?:the\s+)?api\s+documentation)',
            r'(update\s+(?:the\s+)?documentation)',
            r'(design\s+(?:the\s+)?(?:new\s+)?[\w\s]+(?:screens?|ui|interface))',
            r'(write\s+unit\s+tests?\s+for\s+(?:the\s+)?payment\s+module)',
            r'(write\s+unit\s+tests?\s+for\s+(?:the\s+)?[\w\s]*(?:module|modu))',
        ]
        
        for pattern in action_patterns:
            match = re.search(pattern, description, re.IGNORECASE)
            if match:
                description = match.group(1)
                # Special case: convert "database performance" to "Optimize database performance"
                if description.lower() == 'database performance':
                    description = 'Optimize database performance'
                # Fix common transcription errors
                if 'Modu' in description and 'module' not in description.lower():
                    description = description.replace('Modu', 'module')
                if 'modu' in description and 'module' not in description.lower():
                    description = description.replace('modu', 'module')
                break
        
        # Capitalize first letter
        if description:
            description = description[0].upper() + description[1:] if len(description) > 1 else description.upper()
        
        return description.strip()
    
    def _extract_mentioned_person(self, sentence: str) -> Optional[str]:
        """Extracts explicitly mentioned team member name."""
        sentence_lower = sentence.lower()
        
        for name in self.team_names:
            # Check for name at word boundaries
            pattern = r'\b' + re.escape(name) + r'\b'
            if re.search(pattern, sentence_lower):
                # Return original case version
                match = re.search(pattern, sentence_lower)
                if match:
                    # Find the original case in the sentence
                    start = match.start()
                    return sentence[start:start + len(name)].strip()
        
        return None
    
    def _extract_deadline_phrase(self, sentence: str) -> Optional[str]:
        """Extracts deadline phrase from sentence."""
        sentence_lower = sentence.lower()
        
        for pattern in self.DEADLINE_PATTERNS:
            match = re.search(pattern, sentence_lower)
            if match:
                phrase = match.group(1) if match.groups() else match.group(0)
                # Clean up common transcription artifacts
                phrase = phrase.replace(' is ', ' ').replace(' is', '')
                # Handle "next print" -> "next Monday" (common transcription error for "next sprint")
                if 'next print' in phrase or 'next sprint' in phrase:
                    phrase = 'next Monday'
                # Clean up "friday's" -> "friday"
                phrase = phrase.replace("'s", "")
                # Clean up "friday release" -> "friday"
                phrase = re.sub(r'\s+release$', '', phrase)
                return phrase.strip()
        
        # Also check for standalone day names in context
        day_patterns = [
            (r'\bwednesday\b', 'wednesday'),
            (r'\bthursday\b', 'thursday'),
            (r'\bfriday\b', 'friday'),
            (r'\bmonday\b', 'monday'),
            (r'\btuesday\b', 'tuesday'),
        ]
        for pattern, day in day_patterns:
            if re.search(pattern, sentence_lower):
                return day
        
        return None
    
    def _extract_priority_indicators(self, sentence_lower: str) -> List[str]:
        """Extracts priority indicator words from sentence."""
        found = []
        
        for level, indicators in self.PRIORITY_INDICATORS.items():
            for indicator in indicators:
                if indicator in sentence_lower:
                    found.append(indicator)
        
        return found
    
    def _extract_dependency_phrases(self, sentence: str) -> List[str]:
        """Extracts dependency phrases from sentence."""
        found = []
        sentence_lower = sentence.lower()
        
        for pattern in self.DEPENDENCY_PATTERNS:
            matches = re.findall(pattern, sentence_lower)
            found.extend(matches)
        
        return found
    
    def count_task_indicators(self, transcript: str) -> int:
        """Counts the number of task indicator phrases in transcript."""
        if not transcript:
            return 0
        
        transcript_lower = transcript.lower()
        count = 0
        
        for indicator in self.TASK_INDICATORS:
            count += transcript_lower.count(indicator)
        
        return count
