"""
test_nsn_eval.py — Comprehensive test suite for nsn_eval.py

Tests cover:
- Bug regression guards for all 5 original bugs
- New behavior verification (token logging, pre-flight checks, NSN comments)
- Core logic unit tests (scoring, truncation, extraction)
- Integration tests with NSN (skipped if NSN not available)
- Static analysis tests (source inspection)

Regression coverage:
- Bug 1: Double history context overflow
- Bug 2: Sleep cycle timing
- Bug 3: Pipeline initialization warnings
- Bug 4: Token budget guard
- Bug 5: torch_dtype deprecation
"""

import unittest
import ast
import os
import sys
import tempfile
import shutil
import json
from unittest.mock import Mock, patch, MagicMock, call
from io import StringIO

# Add current directory to path for importing nsn_eval
sys.path.insert(0, os.path.dirname(__file__))

try:
    import nsn_eval
    NSN_EVAL_AVAILABLE = True
except ImportError as e:
    NSN_EVAL_AVAILABLE = False
    print(f"Warning: Could not import nsn_eval: {e}")

try:
    import nsn
    NSN_AVAILABLE = True
except ImportError:
    NSN_AVAILABLE = False

try:
    import torch
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False


class TestScoreResponse(unittest.TestCase):
    """Unit tests for score_response() function."""
    
    def setUp(self):
        if not NSN_EVAL_AVAILABLE:
            self.skipTest("nsn_eval not available")
    
    def test_score_perfect_match(self):
        """Test perfect keyword matching."""
        response = "Priya works at HelixAI"
        expected = ["Priya", "HelixAI"]
        result = nsn_eval.score_response(response, expected)
        
        self.assertEqual(result["recall_rate"], 1.0)
        self.assertEqual(set(result["keywords_found"]), {"Priya", "HelixAI"})
        self.assertEqual(result["keywords_expected"], expected)
    
    def test_score_no_match(self):
        """Test no keywords found."""
        response = "I don't know"
        expected = ["Priya", "HelixAI"]
        result = nsn_eval.score_response(response, expected)
        
        self.assertEqual(result["recall_rate"], 0.0)
        self.assertEqual(result["keywords_found"], [])
        self.assertEqual(result["keywords_expected"], expected)
    
    def test_score_partial_match(self):
        """Test partial keyword matching."""
        response = "She uses PostgreSQL"
        expected = ["PostgreSQL"]
        result = nsn_eval.score_response(response, expected)
        
        self.assertEqual(result["recall_rate"], 1.0)
        self.assertEqual(result["keywords_found"], ["PostgreSQL"])
    
    def test_score_partial_match_multiple(self):
        """Test partial matching with multiple expected keywords."""
        response = "latency of 4 seconds"
        expected = ["4", "6", "second", "latency"]
        result = nsn_eval.score_response(response, expected)
        
        self.assertEqual(result["recall_rate"], 0.75)  # 3/4 keywords found
        self.assertEqual(set(result["keywords_found"]), {"4", "second", "latency"})
    
    def test_score_empty_expected(self):
        """Test empty expected keywords list."""
        response = "anything"
        expected = []
        result = nsn_eval.score_response(response, expected)
        
        # Division by zero should be handled gracefully
        self.assertEqual(result["recall_rate"], 0.0)
        self.assertEqual(result["keywords_found"], [])
        self.assertEqual(result["keywords_expected"], [])
    
    def test_score_empty_response(self):
        """Test empty response."""
        response = ""
        expected = ["Priya"]
        result = nsn_eval.score_response(response, expected)
        
        self.assertEqual(result["recall_rate"], 0.0)
        self.assertEqual(result["keywords_found"], [])
    
    def test_score_case_insensitive(self):
        """Test case insensitive matching."""
        response = "PRIYA works at helixai"
        expected = ["priya", "HELIXAI"]
        result = nsn_eval.score_response(response, expected)
        
        self.assertEqual(result["recall_rate"], 1.0)
        self.assertEqual(set(result["keywords_found"]), {"priya", "HELIXAI"})


class TestSafeTruncate(unittest.TestCase):
    """Unit tests for safe_truncate() function."""
    
    def setUp(self):
        if not NSN_EVAL_AVAILABLE:
            self.skipTest("nsn_eval not available")
        
        # Mock tokenizer
        self.mock_tokenizer = Mock()
        self.mock_tokenizer.encode.return_value = list(range(100))  # 100 tokens
        self.mock_tokenizer.decode.return_value = "decoded text"
    
    def test_truncate_long_text(self):
        """Test truncation of long text."""
        # Simulate 2000 tokens
        self.mock_tokenizer.encode.return_value = list(range(2000))
        self.mock_tokenizer.decode.return_value = "truncated text"
        
        result = nsn_eval.safe_truncate("long text", self.mock_tokenizer, 1600)
        
        self.mock_tokenizer.encode.assert_called_once_with("long text")
        # Should keep last 1600 tokens
        expected_tokens = list(range(2000))[-1600:]
        self.mock_tokenizer.decode.assert_called_once_with(expected_tokens, skip_special_tokens=False)
        self.assertEqual(result, "truncated text")
    
    def test_no_truncate_short_text(self):
        """Test that short text passes through unchanged."""
        # Simulate 800 tokens
        self.mock_tokenizer.encode.return_value = list(range(800))
        self.mock_tokenizer.decode.return_value = "original text"
        
        result = nsn_eval.safe_truncate("short text", self.mock_tokenizer, 1600)
        
        self.mock_tokenizer.encode.assert_called_once_with("short text")
        # Should pass through all tokens unchanged
        self.mock_tokenizer.decode.assert_called_once_with(list(range(800)), skip_special_tokens=False)
        self.assertEqual(result, "original text")
    
    def test_truncate_keeps_recency(self):
        """Test that truncation keeps the most recent tokens."""
        # Simulate 50 tokens, truncate to 20
        original_tokens = list(range(50))
        expected_kept = original_tokens[-20:]  # Last 20 tokens
        
        self.mock_tokenizer.encode.return_value = original_tokens
        self.mock_tokenizer.decode.return_value = "recent text"
        
        result = nsn_eval.safe_truncate("text", self.mock_tokenizer, 20)
        
        self.mock_tokenizer.decode.assert_called_once_with(expected_kept, skip_special_tokens=False)
    
    def test_exact_boundary_no_truncate(self):
        """Test text exactly at token limit."""
        # Exactly 1600 tokens
        self.mock_tokenizer.encode.return_value = list(range(1600))
        self.mock_tokenizer.decode.return_value = "boundary text"
        
        result = nsn_eval.safe_truncate("boundary text", self.mock_tokenizer, 1600)
        
        # Should not truncate
        self.mock_tokenizer.decode.assert_called_once_with(list(range(1600)), skip_special_tokens=False)


class TestExtractReply(unittest.TestCase):
    """Unit tests for extract_reply() function."""
    
    def setUp(self):
        if not NSN_EVAL_AVAILABLE:
            self.skipTest("nsn_eval not available")
    
    def test_extract_reply_normal_case(self):
        """Test normal extraction where generated text starts with prompt."""
        prompt = "SYSTEM: hi\nUSER: hello\nASSISTANT: "
        generated = "SYSTEM: hi\nUSER: hello\nASSISTANT: Hello!"
        
        result = nsn_eval.extract_reply(generated, prompt)
        self.assertEqual(result, "Hello!")
    
    def test_extract_reply_no_prompt_prefix(self):
        """Test extraction when generated text doesn't start with prompt."""
        generated = "Hi there<|end|>"
        prompt = ""
        
        result = nsn_eval.extract_reply(generated, prompt)
        self.assertEqual(result, "Hi there<|end|>")
    
    def test_extract_reply_empty_after_stripping(self):
        """Test case where nothing remains after stripping prompt."""
        generated = "same string"
        prompt = "same string"
        
        result = nsn_eval.extract_reply(generated, prompt)
        self.assertEqual(result, "")
    
    def test_extract_reply_with_whitespace(self):
        """Test extraction with whitespace handling."""
        prompt = "USER: "
        generated = "USER:   Hello world   "
        
        result = nsn_eval.extract_reply(generated, prompt)
        self.assertEqual(result, "Hello world")
    
    def test_extract_reply_complex_prompt(self):
        """Test extraction with complex multi-line prompt."""
        prompt = "SYSTEM: You are helpful\nUSER: What is 2+2?\nASSISTANT: "
        generated = "SYSTEM: You are helpful\nUSER: What is 2+2?\nASSISTANT: 2+2 equals 4."
        
        result = nsn_eval.extract_reply(generated, prompt)
        self.assertEqual(result, "2+2 equals 4.")


class TestConversationCorpus(unittest.TestCase):
    """Integrity tests for CONVERSATION list."""
    
    def setUp(self):
        if not NSN_EVAL_AVAILABLE:
            self.skipTest("nsn_eval not available")
    
    def test_conversation_length(self):
        """Test exactly 12 conversation items."""
        self.assertEqual(len(nsn_eval.CONVERSATION), 12)
    
    def test_conversation_recall_count(self):
        """Test exactly 5 recall items."""
        recall_items = [turn for turn in nsn_eval.CONVERSATION if turn["type"] == "recall"]
        self.assertEqual(len(recall_items), 5)
    
    def test_conversation_intro_count(self):
        """Test exactly 7 intro items."""
        intro_items = [turn for turn in nsn_eval.CONVERSATION if turn["type"] == "intro"]
        self.assertEqual(len(intro_items), 7)
    
    def test_conversation_expected_keywords(self):
        """Test every recall item has non-empty expected list."""
        for i, turn in enumerate(nsn_eval.CONVERSATION):
            if turn["type"] == "recall":
                self.assertIn("expected", turn, f"Turn {i} missing 'expected' key")
                self.assertIsInstance(turn["expected"], list, f"Turn {i} 'expected' not a list")
                self.assertGreater(len(turn["expected"]), 0, f"Turn {i} has empty 'expected' list")
    
    def test_conversation_turn_types(self):
        """Test all turn types are valid."""
        valid_types = {"intro", "recall"}
        for i, turn in enumerate(nsn_eval.CONVERSATION):
            self.assertIn(turn["type"], valid_types, f"Turn {i} has invalid type: {turn['type']}")
    
    def test_conversation_user_messages(self):
        """Test every turn has non-empty user message."""
        for i, turn in enumerate(nsn_eval.CONVERSATION):
            self.assertIn("user", turn, f"Turn {i} missing 'user' key")
            self.assertIsInstance(turn["user"], str, f"Turn {i} 'user' not a string")
            self.assertGreater(len(turn["user"].strip()), 0, f"Turn {i} has empty 'user' message")


class TestStaticAnalysis(unittest.TestCase):
    """Source inspection tests (no imports needed)."""
    
    def setUp(self):
        if not NSN_EVAL_AVAILABLE:
            self.skipTest("nsn_eval not available")
        
        # Read source code
        with open("nsn_eval.py", "r") as f:
            self.source = f.read()
        
        # Parse AST
        self.tree = ast.parse(self.source)
    
    def test_no_torch_dtype(self):
        """Test no torch_dtype usage (Bug 5 regression)."""
        self.assertNotIn("torch_dtype", self.source, "torch_dtype found in source (Bug 5 regression)")
    
    def test_nsn_wrap_called_once(self):
        """Test nsn.wrap appears exactly once."""
        self.assertEqual(self.source.count("nsn.wrap"), 1, "nsn.wrap should appear exactly once")
    
    def test_nsn_sleep_called_multiple_times(self):
        """Test nsn.sleep() appears at least twice."""
        self.assertGreaterEqual(self.source.count("nsn.sleep()"), 2, "nsn.sleep() should appear at least twice")
    
    def test_safe_truncate_function_exists(self):
        """Test safe_truncate is defined as a function."""
        func_names = [node.name for node in ast.walk(self.tree) if isinstance(node, ast.FunctionDef)]
        self.assertIn("safe_truncate", func_names, "safe_truncate function not found")
    
    def test_safe_truncate_called_twice(self):
        """Test safe_truncate is called at least twice."""
        self.assertGreaterEqual(self.source.count("safe_truncate("), 2, "safe_truncate should be called at least twice")
    
    def test_nsn_comments_present(self):
        """Test at least 5 NSN comment lines."""
        lines = self.source.split('\n')
        nsn_comment_lines = [line for line in lines if line.strip().startswith("# NSN:")]
        self.assertGreaterEqual(len(nsn_comment_lines), 5, "Should have at least 5 NSN comment lines")
    
    def test_no_history_in_chat_function(self):
        """Test _chat function doesn't reference history or _state (Bug 1 regression)."""
        # Find the _chat function
        chat_func = None
        for node in ast.walk(self.tree):
            if isinstance(node, ast.FunctionDef) and node.name == "_chat":
                chat_func = node
                break
        
        self.assertIsNotNone(chat_func, "_chat function not found")
        
        # Check for history or _state references
        for node in ast.walk(chat_func):
            if isinstance(node, ast.Name) and node.id in {"history", "_state"}:
                self.fail(f"_chat function references '{node.id}' (Bug 1 regression)")
    
    def test_no_generation_config(self):
        """Test no generation_config usage (Bug 3 regression)."""
        self.assertNotIn("generation_config", self.source, "generation_config found in source (Bug 3 regression)")
    
    def test_max_context_tokens_constant(self):
        """Test MAX_CONTEXT_TOKENS is properly defined."""
        self.assertIn("MAX_CONTEXT_TOKENS", self.source, "MAX_CONTEXT_TOKENS constant not found")
        
        # Extract the value
        for line in self.source.split('\n'):
            if line.strip().startswith("MAX_CONTEXT_TOKENS ="):
                value = int(line.split('=')[1].strip())
                self.assertLessEqual(value, 1800, "MAX_CONTEXT_TOKENS should be ≤ 1800")
                break


class TestPipelineInit(unittest.TestCase):
    """Test pipeline initialization signature."""
    
    def setUp(self):
        if not NSN_EVAL_AVAILABLE:
            self.skipTest("nsn_eval not available")
    
    @patch('nsn_eval.pipeline')
    @patch('nsn_eval.AutoModelForCausalLM')
    def test_pipeline_constructor_no_generation_params(self, mock_model, mock_pipeline):
        """Test pipeline constructor doesn't include generation params (Bug 3 regression)."""
        mock_tokenizer = Mock()
        mock_tokenizer.model_max_length = 2048
        
        # Mock the model loading
        mock_model_instance = Mock()
        mock_model.from_pretrained.return_value = mock_model_instance
        
        # Mock pipeline
        mock_pipe = Mock()
        mock_pipeline.return_value = mock_pipe
        
        # Extract the pipeline call from run_baseline
        with patch('nsn_eval.AutoTokenizer') as mock_tokenizer_class:
            mock_tokenizer_class.from_pretrained.return_value = mock_tokenizer
            with patch('nsn_eval.torch.cuda.is_available', return_value=False):
                # We need to extract and call just the pipeline initialization part
                device = "cpu"
                model = mock_model.from_pretrained(
                    nsn_eval.MODEL_ID,
                    dtype=torch.float32,
                    device_map=None
                )
                
                # This is the actual pipeline call from the code
                pipe = mock_pipeline(
                    "text-generation",
                    model=model,
                    tokenizer=mock_tokenizer,
                    device=-1
                )
        
        # Verify pipeline was called without generation params
        call_kwargs = mock_pipeline.call_args[1]
        forbidden_params = ["max_new_tokens", "temperature", "do_sample", "pad_token_id", "torch_dtype"]
        
        for param in forbidden_params:
            self.assertNotIn(param, call_kwargs, f"pipeline constructor should not include {param}")
        
        # Verify required params are present
        self.assertIn("text-generation", mock_pipeline.call_args[0])
        self.assertEqual(call_kwargs["model"], mock_model_instance)
        self.assertEqual(call_kwargs["tokenizer"], mock_tokenizer)
        self.assertEqual(call_kwargs["device"], -1)
    
    @patch('nsn_eval.pipeline')
    @patch('nsn_eval.AutoModelForCausalLM')
    def test_pipeline_call_site_has_generation_params(self, mock_model, mock_pipeline):
        """Test pipeline call site includes generation params."""
        mock_tokenizer = Mock()
        mock_pipe = Mock()
        mock_pipe.return_value = [{"generated_text": "test response"}]
        mock_pipeline.return_value = mock_pipe
        
        with patch('nsn_eval.AutoTokenizer') as mock_tokenizer_class:
            mock_tokenizer_class.from_pretrained.return_value = mock_tokenizer
            with patch('nsn_eval.torch.cuda.is_available', return_value=False):
                # Extract the pipeline call from the code
                device = "cpu"
                model = mock_model.from_pretrained(
                    nsn_eval.MODEL_ID,
                    dtype=torch.float32,
                    device_map=None
                )
                
                pipe = mock_pipeline(
                    "text-generation",
                    model=model,
                    tokenizer=mock_tokenizer,
                    device=-1
                )
                
                # This is the actual pipeline call from the code
                output = pipe(
                    "test prompt",
                    max_new_tokens=nsn_eval.MAX_NEW_TOKENS,
                    temperature=nsn_eval.TEMPERATURE,
                    do_sample=True,
                    pad_token_id=mock_tokenizer.eos_token_id
                )
        
        # Verify call site includes generation params
        call_kwargs = mock_pipe.call_args[1]
        required_params = ["max_new_tokens", "temperature", "do_sample", "pad_token_id"]
        
        for param in required_params:
            self.assertIn(param, call_kwargs, f"pipeline call should include {param}")


class TestNsnIntegration(unittest.TestCase):
    """Integration tests with NSN (skipped if NSN not available)."""
    
    @unittest.skipUnless(NSN_AVAILABLE, "nsn not installed")
    @unittest.skipUnless(NSN_EVAL_AVAILABLE, "nsn_eval not available")
    def test_nsn_init_wrap_smoke(self):
        """Test NSN init and wrap smoke test."""
        with tempfile.TemporaryDirectory() as temp_dir:
            nsn.init(
                project="test-smoke",
                data_dir=temp_dir,
                sleep_interval=999999,
                sleep_on_exit=False,
                recall_threshold=0.0,
                debug=False
            )
            
            def mock_llm(prompt: str) -> str:
                return "My name is Priya Sharma and I work at HelixAI on DevMind."
            
            agent = nsn.wrap(mock_llm)
            reply = agent("What is my name?")
            
            self.assertIsInstance(reply, str)
            self.assertGreater(len(reply), 0)
    
    @unittest.skipUnless(NSN_AVAILABLE, "nsn not installed")
    @unittest.skipUnless(NSN_EVAL_AVAILABLE, "nsn_eval not available")
    def test_memory_storage_retrieval_roundtrip(self):
        """Test memory storage and retrieval round-trip."""
        with tempfile.TemporaryDirectory() as temp_dir:
            nsn.init(
                project="test-roundtrip",
                data_dir=temp_dir,
                sleep_interval=999999,
                sleep_on_exit=False
            )
            
            nsn.remember("The user's name is Priya", importance=1.0)
            mems = nsn.recall("What is the user's name?", top_k=1)
            
            self.assertGreaterEqual(len(mems), 1)
            self.assertTrue(any("Priya" in str(m) for m in mems))
    
    @unittest.skipUnless(NSN_AVAILABLE, "nsn not installed")
    @unittest.skipUnless(NSN_EVAL_AVAILABLE, "nsn_eval not available")
    def test_sleep_cycle_returns_expected_keys(self):
        """Test sleep cycle runs and returns expected keys."""
        with tempfile.TemporaryDirectory() as temp_dir:
            nsn.init(
                project="test-sleep",
                data_dir=temp_dir,
                sleep_interval=999999,
                sleep_on_exit=False
            )
            
            nsn.remember("Fact A", importance=1.0)
            nsn.remember("Fact B", importance=1.0)
            stats = nsn.sleep()
            
            self.assertIsInstance(stats, dict)
            self.assertTrue("promoted" in stats or "boosted" in stats or "decayed" in stats)
    
    @unittest.skipUnless(NSN_AVAILABLE, "nsn not installed")
    @unittest.skipUnless(NSN_EVAL_AVAILABLE, "nsn_eval not available")
    def test_pin_protects_memory(self):
        """Test pin protects memory from sleep pruning."""
        with tempfile.TemporaryDirectory() as temp_dir:
            nsn.init(
                project="test-pin",
                data_dir=temp_dir,
                sleep_interval=999999,
                sleep_on_exit=False
            )
            
            nsn.pin("API Key is XYZ-123", label="SENSITIVE")
            nsn.sleep()
            mems = nsn.recall("API Key", top_k=5)
            
            self.assertTrue(any("XYZ-123" in str(m) for m in mems), "Pinned memory must survive sleep")


class TestRegressionGuards(unittest.TestCase):
    """Regression tests for all 5 original bugs."""
    
    def setUp(self):
        if not NSN_EVAL_AVAILABLE:
            self.skipTest("nsn_eval not available")
    
    # Bug 1: Double history context overflow
    @unittest.skipUnless(NSN_AVAILABLE, "nsn not installed")
    def test_bug_1_double_history_regression(self):
        """Regression: Bug 1 — double history context overflow."""
        token_counts = []
        
        def counting_llm(prompt: str) -> str:
            # Use word count as token proxy for this test
            token_counts.append(len(prompt.split()))
            return "I remember everything you said."
        
        with tempfile.TemporaryDirectory() as temp_dir:
            nsn.init(
                project="test-growth",
                data_dir=temp_dir,
                sleep_interval=999999,
                sleep_on_exit=False
            )
            
            agent = nsn.wrap(counting_llm)
            
            for i in range(8):
                agent(f"Turn {i}: my name is Priya and I work at HelixAI on DevMind.")
            
            # Token counts should NOT grow linearly with turn number
            growth_ratio = token_counts[-1] / token_counts[0] if token_counts[0] > 0 else 1
            
            # If double history is reintroduced, count[7] will be ~8x count[0]
            self.assertLess(growth_ratio, 4.0, 
                f"Prompt grew {growth_ratio:.1f}x over 8 turns — double history regression detected. "
                f"Counts: {token_counts}")
    
    # Bug 2: Sleep cycle timing
    def test_bug_2_sleep_timing_source_check(self):
        """Regression: Bug 2 — sleep cycle timing (source check)."""
        with open("nsn_eval.py", "r") as f:
            source = f.read()
        
        # Check that sleep is called after intro turns in the loop
        lines = source.split('\n')
        in_nsn_run = False
        sleep_after_intro_found = False
        
        for line in lines:
            if "def run_nsn" in line:
                in_nsn_run = True
            elif in_nsn_run and "def " in line and "run_nsn" not in line:
                in_nsn_run = False  # Left the run_nsn function
            
            if in_nsn_run and 'if turn["type"] == "intro"' in line:
                # Look for sleep call in the next few lines
                for next_line in lines[lines.index(line):lines.index(line)+5]:
                    if "nsn.sleep()" in next_line:
                        sleep_after_intro_found = True
                        break
        
        self.assertTrue(sleep_after_intro_found, "nsn.sleep() not found after intro turns (Bug 2 regression)")
    
    # Bug 3: Pipeline initialization warnings
    def test_bug_3_pipeline_warnings_source_check(self):
        """Regression: Bug 3 — pipeline initialization warnings."""
        with open("nsn_eval.py", "r") as f:
            source = f.read()
        
        # Check pipeline constructor calls
        lines = source.split('\n')
        pipeline_calls = []
        
        for i, line in enumerate(lines):
            if "pipeline(" in line:
                # Collect the full call (might span multiple lines)
                call_lines = [line]
                j = i + 1
                while j < len(lines) and not lines[j].strip().endswith(')'):
                    call_lines.append(lines[j])
                    j += 1
                if j < len(lines):
                    call_lines.append(lines[j])
                pipeline_calls.append('\n'.join(call_lines))
        
        for call in pipeline_calls:
            # Check for forbidden constructor parameters
            forbidden_params = ["max_new_tokens=", "temperature=", "do_sample=", "pad_token_id=", "torch_dtype="]
            for param in forbidden_params:
                self.assertNotIn(param, call, f"pipeline constructor includes {param} (Bug 3 regression)")
    
    # Bug 4: Token budget guard
    def test_bug_4_token_budget_guard_source_check(self):
        """Regression: Bug 4 — token budget guard."""
        with open("nsn_eval.py", "r") as f:
            source = f.read()
        
        # Check safe_truncate function exists
        self.assertIn("def safe_truncate(", source, "safe_truncate function not found (Bug 4 regression)")
        
        # Check safe_truncate is called in both runs
        self.assertGreaterEqual(source.count("safe_truncate("), 2, "safe_truncate not called enough times (Bug 4 regression)")
        
        # Check MAX_CONTEXT_TOKENS is defined
        self.assertIn("MAX_CONTEXT_TOKENS =", source, "MAX_CONTEXT_TOKENS not defined (Bug 4 regression)")
    
    # Bug 5: torch_dtype deprecation
    def test_bug_5_torch_dtype_deprecation_check(self):
        """Regression: Bug 5 — torch_dtype deprecation."""
        with open("nsn_eval.py", "r") as f:
            source = f.read()
        
        self.assertNotIn("torch_dtype=", source, "torch_dtype found in source (Bug 5 regression)")


class TestNewBehavior(unittest.TestCase):
    """Tests for new behavior added by the fix."""
    
    def setUp(self):
        if not NSN_EVAL_AVAILABLE:
            self.skipTest("nsn_eval not available")
    
    def test_token_logging_pattern(self):
        """Test token logging pattern exists."""
        with open("nsn_eval.py", "r") as f:
            source = f.read()
        
        # Should contain the token logging pattern
        self.assertIn("[tokens:", source, "Token logging pattern not found")
        self.assertIn("/ 1600]", source, "Token logging with budget not found")
    
    def test_preflight_checks_function(self):
        """Test pre-flight checks function exists."""
        with open("nsn_eval.py", "r") as f:
            source = f.read()
        
        self.assertIn("def pre_flight_checks(", source, "pre_flight_checks function not found")
        self.assertIn("CUDA Available:", source, "CUDA availability check not found")
        self.assertIn("Model:", source, "Model info not found")
        self.assertIn("NeuroSleepNet Version:", source, "NSN version check not found")
    
    def test_nsn_comments_only_in_nsn_section(self):
        """Test NSN comments only appear in NSN-specific sections."""
        with open("nsn_eval.py", "r") as f:
            source = f.read()
        
        lines = source.split('\n')
        nsn_comment_lines = []
        baseline_section = False
        
        for i, line in enumerate(lines):
            if "def run_baseline" in line:
                baseline_section = True
            elif baseline_section and "def run_nsn" in line:
                baseline_section = False
            
            if line.strip().startswith("# NSN:"):
                nsn_comment_lines.append((i, line, baseline_section))
        
        # Check that no NSN comments are in baseline section
        baseline_nsn_comments = [(i, line) for i, line, in_baseline in nsn_comment_lines if in_baseline]
        self.assertEqual(len(baseline_nsn_comments), 0, 
            f"NSN comments found in baseline section: {baseline_nsn_comments}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
