from pb.v1alpha1 import element_pb2
from lxml import html

from orby.digitalagent.utils.dom_utils import ELEMENTS_TO_REMOVE


TAG_ROLE_MAP = {
    "a": "link",
    "button": "button",
    "input": "textbox",  # default to textbox for input (can vary based on type)
    "select": "combobox",
    "textarea": "textbox",
    "section": "region",
    "nav": "navigation",
    "header": "banner",
    "footer": "contentinfo",
    "article": "article",
    "aside": "complementary",
    "h1": "heading",
    "h2": "heading",
    "h3": "heading",
    "h4": "heading",
    "h5": "heading",
    "h6": "heading",
    "table": "table",
    "tr": "row",
    "th": "columnheader",
    "td": "cell",
    "ul": "list",
    "ol": "list",
    "li": "listitem",
    "form": "form",
}


def create_element_from_html(html_str: str) -> element_pb2.Element:
    tree = html.fromstring(html_str)

    def dfs(tree: html.HtmlComment) -> element_pb2.Element:
        children = []
        if tree.text and tree.text.strip():
            children.append(element_pb2.Element(description=tree.text.strip()))
        for child in tree:
            child_element = dfs(child)
            children.append(child_element)
            if child.tail and child.tail.strip():
                children.append(element_pb2.Element(description=child.tail.strip()))

        return element_pb2.Element(
            type=tree.tag,
            attributes=tree.attrib,
            children=children,
        )

    return dfs(tree)


def create_element_from_dom_frames(dom_frames: dict) -> element_pb2.Element:
    """
    Create an element proto from the dom frames recorded in action crawler

    Args:
        dom_frames: A dictionary representing the dom frames

    Returns:
        element_pb2.Element: The root element of the dom tree with all children populated
    """
    element_id = -1

    def _traverse_dom_frames(dom_frame: dict) -> element_pb2.Element:
        """Recursively traverse the dom frames and create the element proto representation"""
        nonlocal element_id
        element_id += 1
        # If we have a text element, we just store the text
        if "text" in dom_frame:
            element = element_pb2.Element(
                description=dom_frame["text"],
                label=dom_frame["text"],
            )
        else:
            element = element_pb2.Element(
                id=str(element_id),
                type=dom_frame["tag"].lower(),
                bounding_box=element_pb2.Rect(
                    x=dom_frame["boundingBox"]["x"],
                    y=dom_frame["boundingBox"]["y"],
                    width=dom_frame["boundingBox"]["width"],
                    height=dom_frame["boundingBox"]["height"],
                ),
                cursor=dom_frame["cursor"],
                at_top=dom_frame["atTop"],
                attributes={str(k): str(v) for k, v in dom_frame["attributes"].items()},
            )
            for i in range(len(dom_frame["children"])):
                element.children.append(_traverse_dom_frames(dom_frame["children"][i]))
        return element

    root_element = _traverse_dom_frames(dom_frames)
    return root_element


def flatten_dom_to_str(
    tree: element_pb2.Element,
    extra_properties: dict = None,
    skip_generic: bool = True,
    remove_redundant_static_text: bool = True,
    hide_bid_if_invisible: bool = False,
    hide_all_children: bool = False,
    indent_character: str = "\t",
) -> str:
    """Formats the DOM tree into a string text"""

    def get_role(node: element_pb2.Element):
        if "role" in node.attributes:
            return node.attributes["role"]
        if node.type.lower() in TAG_ROLE_MAP:
            return TAG_ROLE_MAP[node.type.lower()]
        return "generic"

    def get_text(node: element_pb2.Element) -> str:
        if node.description:
            return node.description.strip()
        result = ""
        for child in node.children:
            if child.description:
                result += " " + get_text(child)
            else:
                result += "\n" + get_text(child)
        return result.strip()

    def get_name(node: element_pb2.Element) -> str:
        candidates = [
            node.attributes.get("aria-label", "").strip(),
            node.attributes.get("title", "").strip(),
            node.attributes.get("name", "").strip(),
            node.input_value.strip(),
            node.attributes.get("aria-valuetext", "").strip(),
            node.attributes.get("aria-valuenow", "").strip(),
        ]
        for i in candidates:
            if i:
                return i
        return ""

    new_bid = 1

    def dfs(
        node: element_pb2.Element,
        depth: int,
        parent_node_filtered: bool,
        parent_node_name: str,
    ) -> str:
        tree_str = ""
        indent = indent_character * depth
        if node.type in ELEMENTS_TO_REMOVE:
            return ""
        if node.description:
            return f"{indent}StaticText {repr(node.description.strip())}"
        skip_node = False  # node will not be printed, with no effect on children nodes
        filter_node = (
            False  # node will not be printed, possibly along with its children nodes
        )
        node_role = get_role(node)
        if node_role == "presentation":
            skip_node = True

        node_name = get_name(node)

        node_value = node.input_value

        # extract bid
        bid = node.id
        if not bid:
            nonlocal new_bid
            bid = new_bid
            new_bid += 1
            node.id = str(new_bid)

        # extract node attributes
        attributes = []
        if node.checked:
            attributes.append(f"checked=true")
        if node.focus:
            attributes.append(f"focused=true")
        if node.hover:
            attributes.append(f"hover=true")
        if node.active:
            attributes.append(f"active=true")

        if skip_generic and node_role == "generic" and not attributes:
            skip_node = True

        if hide_all_children and parent_node_filtered:
            skip_node = True

        if node_role == "StaticText":
            if parent_node_filtered:
                skip_node = True
            elif remove_redundant_static_text and node_name in parent_node_name:
                skip_node = True

        # actually print the node string
        if not skip_node:
            if node_role == "generic" and not node_name:
                node_str = f"{node_role}"
            else:
                node_str = f"{node_role} {repr(node_name.strip())}"

            if not (
                bid is None
                or (
                    hide_bid_if_invisible
                    and extra_properties.get(bid, {}).get("visibility", 0) < 0.5
                )
            ):
                node_str = f"[{bid}] " + node_str

            if node_value:
                node_str += f" value={repr(node_value)}"

            if attributes:
                node_str += ", ".join([""] + attributes)

            tree_str += f"{indent}{node_str}"

        for child in node.children:
            # mark this to save some tokens
            child_depth = depth if skip_node else (depth + 1)
            child_str = dfs(
                child,
                child_depth,
                parent_node_filtered=filter_node,
                parent_node_name=node_name,
            )
            if child_str:
                if tree_str:
                    tree_str += "\n"
                tree_str += child_str

        return tree_str

    tree_str = dfs(tree, 0, False, "")
    return tree_str
