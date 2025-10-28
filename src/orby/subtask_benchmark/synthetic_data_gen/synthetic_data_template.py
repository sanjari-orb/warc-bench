from typing import List, Union, Literal, Optional
from pydantic import BaseModel, validator

# Allowed values for subtask_type (from your prompt)
SUBTASK_TYPES = [
    "dropdown_option_selection",
    "table_manipulation",
    "menu_navigation",
    "computation",
    "search_and_autocomplete",
    "icon_recognition",
    "data_extraction",
    "form_filling",
    "datepicker",
    "sheet_editing",
    "document_editing",
    "pagination",
    "dialog_boxes",
    "generic_grounding",
    "list_navigation",
    "drag_and_drop_interaction",
]

# Allowed values for eval_type
EVAL_TYPES = [
    "string_matcher",
    "url_matcher",
    "js_matcher",
    "json_matcher",
]


class SyntheticDataTemplate(BaseModel):
    data_path: str  # fixed value per dataset, but string in each row
    subtask_type: List[str]
    subtask_goal: str
    start_url: str
    eval_type: Literal[*EVAL_TYPES]
    evaluation: Union[str, dict, list]  # Can be a string, JSON dict, or list

    @validator("subtask_type", pre=True)
    def check_subtask_type(cls, v):
        # Accept comma-separated string or list
        if isinstance(v, str):
            types = [s.strip() for s in v.split(",")]
        elif isinstance(v, list):
            types = v
        else:
            raise ValueError("subtask_type must be a string or list")
        # Validate allowed types
        # for t in types:
        #     if t not in SUBTASK_TYPES:
        #         raise ValueError(f"Invalid subtask_type: {t}")
        if not (1 <= len(types) <= 3):
            raise ValueError("subtask_type must have 1 to 3 values")
        return types

    @validator("eval_type")
    def check_eval_type(cls, v):
        if v not in EVAL_TYPES:
            raise ValueError(f"Invalid eval_type: {v}")
        return v

    @validator("evaluation")
    def check_evaluator(cls, v, values):
        # If eval_type is json_matcher, evaluator should be dict or list
        if values.get("eval_type") == "json_matcher" and not isinstance(
            v, (dict, list)
        ):
            raise ValueError("evaluator must be a dict or list for json_matcher")
        # If eval_type is string_matcher or url_matcher, evaluator should be string
        if values.get("eval_type") in (
            "string_matcher",
            "url_matcher",
        ) and not isinstance(v, str):
            raise ValueError(
                "evaluator must be a string for string_matcher or url_matcher"
            )
        # If eval_type is js_matcher, evaluator type doesn't matter as it's not used
        return v


# Example usage for parsing a row:
# row = SyntheticDataRow(
#     data_path="sfusd/school_finder.wacz",
#     subtask_type="pagination",
#     subtask_goal="Open the 4th page of the school directory",
#     start_url="https://www.sfusd.edu/schools/directory",
#     eval_type="url_matcher",
#     evaluator="https://www.sfusd.edu/schools/directory?page=3"
# )
