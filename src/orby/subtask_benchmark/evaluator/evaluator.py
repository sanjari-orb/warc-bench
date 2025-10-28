## Evaluator methods for Subtask benchmark tasks
import json
import logging
from typing import List, Dict, Any, Type
import playwright.sync_api
from abc import ABC, abstractmethod
from collections import Counter
import codecs


logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("subtask_benchmark.evaluator")


class BaseEvaluator(ABC):
    @abstractmethod
    def evaluate(self, answer: str, page: playwright.sync_api.Page, **kwargs) -> float:
        pass


class EvaluatorRegistry:
    """
    Registry for evaluators.
    """

    _evaluators: Dict[str, Type[BaseEvaluator]] = {}

    @classmethod
    def register(cls, eval_type: str):
        """Class decorator to register evaluator classes."""

        def decorator(evaluator_class: Type[BaseEvaluator]) -> Type[BaseEvaluator]:
            cls._evaluators[eval_type] = evaluator_class
            return evaluator_class

        return decorator

    @classmethod
    def create(cls, eval_type: str, evaluation_script: str) -> BaseEvaluator:
        """Creates and returns an evaluator instance of the specified type.

        Args:
            eval_type: string, Type of evaluator to create
            evaluation_script: string, Script/Ground-Truth used by the evaluator

        Returns:
            BaseEvaluator: Instance of the requested evaluator type
        """
        if eval_type not in cls._evaluators:
            raise ValueError(f"Unknown evaluator type: {eval_type}")

        evaluator_class = cls._evaluators[eval_type]
        return evaluator_class(evaluation_script)


@EvaluatorRegistry.register("js_matcher")
class JSEvaluator(BaseEvaluator):
    """
    Evaluator for JavaScript-based matching tasks.

    This evaluator executes JavaScript code in a browser page context to determine if a task
    has been completed successfully. It evaluates DOM state and other browser conditions
    specified in the evaluation script.
    """

    def __init__(self, evaluation_script: str):
        self.evaluation_script = evaluation_script

    def evaluate(self, answer: str, page: playwright.sync_api.Page) -> float:
        """Evaluates JavaScript code in the browser page context to determine task completion.

        Args:
            page (playwright.sync_api.Page): The Playwright page object to evaluate the script in

        Returns:
            float: 1.0 if the evaluation script returns True, 0.0 otherwise
        """
        reward = 0
        try:
            # Evaluate the evaluation script
            result = page.evaluate(self.evaluation_script)
            if result:
                reward = 1
        except Exception as e:
            logger.error(
                f"Error evaluating the evaluation script: {e}. This typically means the agent failed to complete the task."
            )

        return reward


@EvaluatorRegistry.register("json_matcher")
class JSONEvaluator(BaseEvaluator):
    """
    Evaluator for JSON-based matching tasks.

    This evaluator checks if the answer JSON string contains all the items in the goal JSON string.
    """

    def __init__(self, serialized_goal_json: str):
        self.goal_json = json.loads(serialized_goal_json)

    def evaluate(
        self, serialized_answer_json: str, page: playwright.sync_api.Page
    ) -> float:
        """Evaluates if the answer JSON string contains all items in the goal JSON."""
        logger.info(
            f"answer_string: {serialized_answer_json}, goal_json: {self.goal_json}"
        )

        if serialized_answer_json == "":
            logger.error("Answer is empty")
            return 0

        try:
            original_string = codecs.decode(serialized_answer_json, 'unicode_escape')
            answer_json = json.loads(original_string)
        except json.decoder.JSONDecodeError as e:
            logger.error(f"Error parsing answer JSON: {e}")
            return 0

        if type(answer_json) != type(self.goal_json):
            return 0

        if isinstance(answer_json, dict):
            if set(answer_json.keys()) != set(self.goal_json.keys()):
                return 0

            for key in self.goal_json.keys():
                if str(answer_json[key]).strip() != str(self.goal_json[key]).strip():
                    return 0

            return 1

        elif isinstance(answer_json, list):
            if len(answer_json) != len(self.goal_json):
                return 0

            result = Counter([str(x) for x in answer_json]) == Counter(
                [str(x) for x in self.goal_json]
            )
            if result:
                return 1
            else:
                logger.info(f"answer_json: {answer_json}, goal_json: {self.goal_json}")
                return 0

        else:
            return answer_json == self.goal_json


@EvaluatorRegistry.register("string_matcher")
class StringEvaluator(BaseEvaluator):
    """
    Evaluator for string-based matching tasks.

    This evaluator checks if the answer string contains all the items in the goal array.
    """

    def __init__(self, evaluation_string: str):
        self.goal_string = evaluation_string

    def evaluate(self, answer_string: str, page: playwright.sync_api.Page) -> float:
        """Evaluates if the answer string contains all items in the goal array."""
        original_string = codecs.decode(answer_string, 'unicode_escape')

        print(f"answer_string: {original_string}, goal_string: {self.goal_string}")

        if original_string.strip() == self.goal_string.strip():
            return 1
        else:
            return 0


@EvaluatorRegistry.register("url_matcher")
class URLEvaluator(BaseEvaluator):
    """
    Evaluator for URL-based matching tasks.

    This evaluator checks if the answer URL matches the goal URL.
    """

    def __init__(self, evaluation_script: str):
        self.goal_url = evaluation_script

    def evaluate(self, answer_url: str, page: playwright.sync_api.Page) -> float:
        logger.info(f"answer_url: {page.url}, goal_url: {self.goal_url}")
        return float(page.url == self.goal_url)