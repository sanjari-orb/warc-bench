from typing import Any, Callable
from pb.v1alpha1 import element_pb2


ELEMENTS_TO_REMOVE = set(
    {
        "script",
        "style",
        "noscript",
        "meta",
        "link",
        "head",
    }
)

ATTRIBUTES_TO_KEEP = set(
    {
        "aria-label",
        "aria-details",
        "alt",
        "title",
        "type",
        "placeholder",
        "name",
        "role",
        "value",
        "checked",
    }
)

# Those elements will be kept even if they do not have any attributes.
ELEMENTS_TO_KEEP_REGARDLESS_OF_ATTRIBUTES = set(
    {
        "a",
        "button",
        "input",
        "textarea",
        "select",
        "form",
        "table",
        "tr",
        "td",
        "th",
        "submit",
    }
)

ELEMENTS_TO_KEEP_REGARDLESS_OF_VISIBILITY = set(
    {
        "option",
    }
)


def find_acted_upon_node(node: element_pb2.Element) -> element_pb2.Element | None:
    if node.acted_upon:
        return node
    for child in node.children:
        result = find_acted_upon_node(child)
        if result:
            return result
    return None


def find_node_by_attribute(
    node: element_pb2.Element,
    key: str,
    value: str,
    ancestors: list[element_pb2.Element] | None = None,
) -> element_pb2.Element | None:
    """Find node by using attribute.

    ancestors will be modified to include the target element's ancestors. Root will be the last element.
    """
    if node.attributes.get(key, "").strip() == value:
        return node
    for child in node.children:
        result = find_node_by_attribute(child, key, value, ancestors=ancestors)
        if result:
            if ancestors is not None:
                ancestors.append(node)
            return result
    return None


def get_bid(node: element_pb2.Element) -> str | None:
    bid = node.attributes.get("aria-description", None)
    if not bid and not node.id:
        return None
    if not bid:
        return node.id
    return bid[len("browsergym_id_") :].strip()


def _is_element_visible(node: element_pb2.Element, parent_visibility: bool = True):
    if node.type:
        if node.at_top or node.type == "document":
            return True
        if parent_visibility and node.type in ELEMENTS_TO_KEEP_REGARDLESS_OF_VISIBILITY:
            return True
        return False
    return True


def _format_attributes(attributes: dict) -> str:
    components = []
    for key in attributes:
        components.append(f'{key}="{attributes[key]}"')
    if not components:
        return ""
    return " " + " ".join(components)


def _get_semantic_attributes(node: element_pb2.Element) -> dict[str, str]:
    attributes = {}
    for key in ATTRIBUTES_TO_KEEP:
        if key in node.attributes and node.attributes[key].strip():
            if len(node.attributes[key].strip()) < 128:
                attributes[key] = node.attributes[key].strip()
    return attributes


def _get_state_attributes(node: element_pb2.Element) -> dict[str, str]:
    attributes = {}
    if node.input_value:
        attributes["value"] = node.input_value
    if node.focus:
        attributes["focused"] = "focused"
    if node.checked:
        attributes["checked"] = "checked"
    if node.active:
        attributes["active"] = "active"
    if node.hover:
        attributes["hover"] = "hover"
    return attributes


def html_to_string(
    node: element_pb2.Element,
    indent_character: str = "\t",
    keep_all_attributes: bool = False,
    keep_bid: bool = True,
    keep_closing_tag: bool = False,
    keep_bid_for_select_only: bool = False,
    compact: bool = False,  # If True, option will be represented in a more compact way.
    skip_visibility_check: bool = True,  # If True, elements will be included in the text representation regardless of whether they are visible or not.
) -> str:

    def dfs(
        node: element_pb2.Element, parent_visibility: bool = True, indent: int = 0
    ) -> tuple[str, bool]:
        """Returns a string representing the node and a bool indicating whether the node is an element."""
        if not node.type:  # text node
            if not parent_visibility:
                return "", False
            return indent_character * indent + node.description.strip(), False
        if node.type in ELEMENTS_TO_REMOVE:
            return "", False

        should_skip_node = False
        if keep_all_attributes:
            attributes = dict(node.attributes)
        else:
            attributes = _get_semantic_attributes(node)
        if (
            not attributes
            and not node.type in ELEMENTS_TO_KEEP_REGARDLESS_OF_ATTRIBUTES
        ):
            should_skip_node = True

        children = []
        any_node_child = False
        visibility = skip_visibility_check or _is_element_visible(
            node,
            parent_visibility=parent_visibility,
        )

        for child in node.children:
            s, child_is_node = dfs(
                child,
                parent_visibility=visibility,
                indent=(indent + 1) if not should_skip_node else indent,
            )
            if s.strip():
                children.append(s)
            if child_is_node:
                any_node_child = True
        if not visibility and not children:
            return "", False

        if not children and should_skip_node:
            return "", False
        if should_skip_node and any_node_child:
            return "\n".join([child for child in children]), any_node_child

        if not attributes and not children and node.cursor != "pointer":
            return "", False

        bid = get_bid(node)
        if keep_bid and not bid:
            return "", False

        prefix = ""
        if keep_bid:
            prefix = f"[{bid}] "
        if keep_bid_for_select_only and node.type != "select":
            prefix = ""
        if node.type == "option" and not node.at_top:
            prefix = ""

        if compact:
            if node.type == "option":
                value = node.attributes.get("value")
                name = " ".join([child.strip() for child in children])
                return indent_character * indent + f"{prefix} {value}: {name}", True

        attributes.update(_get_state_attributes(node))
        opening_tag = f"{prefix}<{node.type}{_format_attributes(attributes)}>"
        closing_tag = f"</{node.type}>"
        if not children:
            result = indent_character * indent + opening_tag
            if keep_closing_tag:
                result += closing_tag
            return (
                result,
                True,
            )

        # All children are text. so we don't skip.
        child_joiner = "\n"
        if should_skip_node:
            child_joiner = "\n" + indent_character + " " * len(prefix)
        result = (
            indent_character * indent
            + opening_tag
            + "\n"
            + (indent_character + " " * len(prefix) if should_skip_node else "")
            + child_joiner.join([child for child in children])
        )
        if keep_closing_tag:
            result += "\n" + indent_character * indent + " " * len(prefix) + closing_tag

        return (
            result,
            True,
        )

    return dfs(node)[0]


def populate_element_id_with_browsergym_id(node: element_pb2.Element) -> None:
    """
    Populate the id field of all elements with their browsergym_id attribute.

    Args:
        node (element_pb2.Element): The root element.
    """

    def dfs(node: element_pb2.Element):
        bid = get_bid(node)
        if bid:
            node.id = bid
        for child in node.children:
            dfs(child)

    dfs(node)


def make_id_bbox_map_from_element_proto(
    node: element_pb2.Element,
) -> dict[str, element_pb2.Rect]:
    """
    Create a mapping from element id to bounding box.

    Args:
        node (element_pb2.Element): The root element.

    Returns:
        dict[str, list[float]]: A mapping from element id to bounding box.
    """
    id_bbox_map = {}

    def dfs(node: element_pb2.Element):
        if node.type:
            id_bbox_map[node.id] = node.bounding_box
        for child in node.children:
            dfs(child)

    dfs(node)
    return id_bbox_map


def find_element_by_bid(
    node: element_pb2.Element, bid: str, bid_location: str = "attributes"
) -> element_pb2.Element | None:
    """
    Find an element by its browsergym_id.

    Args:
        node (element_pb2.Element): The root element.
        bid (str): The browsergym_id.
        bid_location (str): The location of the browsergym_id. Can be
            - "attributes": we try to find the bid in node.attributes["bid"]
            - "id": we try to find the bid in node.id
            Default is "attributes".

    Returns:
        element_pb2.Element: The element with the given browsergym_id, or None if not found.
    """

    def _has_bid(node: element_pb2.Element, bid_location: str) -> bool:
        if bid_location == "attributes":
            return node.attributes.get("bid", "") == bid
        return node.id == bid

    def dfs(node: element_pb2.Element):
        if _has_bid(node, bid_location):
            return node
        for child in node.children:
            result = dfs(child)
            if result:
                return result
        return None

    return dfs(node)


def compress_dom(
    root_element: element_pb2.Element,
    orbot_dom_options: dict[str, Any],
    token_counter: Callable[[str], int],
    max_tokens: int,
) -> str:
    # make a copy so that the original options are not updated
    orbot_dom_options = {key: orbot_dom_options[key] for key in orbot_dom_options}
    orbot_dom_options["compact"] = True
    orbot_dom_options["keep_closing_tag"] = False
    orbot_dom_options["skip_visibility_check"] = False
    html = html_to_string(root_element, **orbot_dom_options)
    # TODO: consider moving text hints outside this function
    if token_counter(html) <= max_tokens:
        return (
            "The below HTML only shows elements that are visible in the screenshot. Scroll to reveal more contents.\n"
            + html
        )
    orbot_dom_options["keep_bid_for_select_only"] = True
    html = html_to_string(root_element, **orbot_dom_options)
    if token_counter(html) <= max_tokens:
        return (
            "The below HTML only shows elements that are visible in the screenshot. Scroll to reveal more contents.\n"
            + html
        )
    return "HTML is too large. Please use coordinate actions."


def find_center_point_of_element(element: element_pb2.Element) -> tuple[float, float]:
    """
    Find the center point of an element.

    Args:
        element (element_pb2.Element): The element.

    Returns:
        tuple[float, float]: The center point.
    """
    x = element.bounding_box.x
    y = element.bounding_box.y
    w = element.bounding_box.width
    h = element.bounding_box.height

    # TODO (cheng): add offset for iframe. For some reason this is not present in the
    # current proto definition in digital-agent.
    return x + w / 2, y + h / 2
